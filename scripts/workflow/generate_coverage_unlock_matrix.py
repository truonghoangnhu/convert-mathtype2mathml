#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CONTRACTS_ROOT = Path("out/full-corpus-in-test-validation-20260409-095900")
DEFAULT_OUTPUT_PARENT = Path("out")
DEFAULT_PREFIX = "coverage-unlock-matrix"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _find_jar(candidate: Optional[Path]) -> Path:
    if candidate is not None:
        jar = candidate.resolve()
        if not jar.exists():
            raise FileNotFoundError(f"java jar not found: {jar}")
        return jar
    matches = sorted(Path("target").glob("*-jar-with-dependencies.jar"))
    if matches:
        return matches[-1].resolve()
    raise FileNotFoundError("could not locate built jar under target/")


REQUIRED_TRIGGER_CODES = {
    "canonical_answer_missing",
    "unresolved_reconciliation",
    "answer_source_conflict",
    "summary_vs_local_conflict",
    "summary_vs_solution_conflict",
    "local_vs_solution_conflict",
    "short_answer_value_conflict",
    "boolean_subanswer_conflict",
    "rubric_source_conflict",
}

SECONDARY_TRIGGER_CODES = {
    "missing_rubric_source",
    "document_family_ambiguous",
    "summary_mapping_invalid",
    "low_parse_confidence",
}


def _discover_bundle_dirs(root: Path) -> List[Path]:
    if not root.exists():
        return []
    result: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "manifest.json").is_file() and (child / "question_bank_items.json").is_file():
            result.append(child)
    return result


def _answer_summary_map(exam_bundle: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    mapping: Dict[int, Dict[str, Any]] = {}
    entries = (exam_bundle.get("answer_summary") or {}).get("entries") or []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        qn = str(entry.get("question_number", "") or "")
        if qn.isdigit():
            mapping[int(qn)] = entry
    return mapping


def _rubric_text(item: Dict[str, Any]) -> str:
    rubric = item.get("rubric")
    if not isinstance(rubric, dict):
        return ""
    text = str(rubric.get("rubric_text", "") or "").strip()
    if text:
        return text
    rubric_json = rubric.get("rubric_json")
    if isinstance(rubric_json, dict):
        return str(rubric_json.get("rubric_text", "") or "").strip()
    return ""


def _count_unresolved_items(qb: Dict[str, Any]) -> Dict[str, Any]:
    items = qb.get("items") or []
    missing_answer = 0
    unresolved = 0
    conflict = 0
    rubric_gaps = 0
    essay_count = 0
    rubric_mode_count = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        ak = it.get("answer_key") if isinstance(it.get("answer_key"), dict) else {}
        mode = str((ak or {}).get("mode") or "").strip()
        rec = it.get("reconciliation") if isinstance(it.get("reconciliation"), dict) else {}
        status = str((rec or {}).get("status") or "").strip()
        qtype = str(it.get("question_type") or "").strip()

        if qtype == "essay":
            essay_count += 1
        if mode == "rubric":
            rubric_mode_count += 1

        if mode == "none" or status == "blocked":
            missing_answer += 1
        if status in {"conflict", "needs_review", "blocked"}:
            unresolved += 1
        if status == "conflict":
            conflict += 1

        if (qtype == "essay" or mode == "rubric") and not _rubric_text(it):
            rubric_gaps += 1

    return {
        "item_count": int(qb.get("item_count") or len(items)),
        "missing_answer_count": missing_answer,
        "unresolved_reconciliation_count": unresolved,
        "conflict_item_count": conflict,
        "rubric_gap_count": rubric_gaps,
        "essay_count": essay_count,
        "rubric_mode_count": rubric_mode_count,
    }


def _missing_fillable_via_answer_summary(qb: Dict[str, Any], answer_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    items = qb.get("items") or []
    missing_qns: List[int] = []
    fillable_qns: List[int] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        qn = int(it.get("question_number") or 0)
        if qn <= 0:
            continue
        ak = it.get("answer_key") if isinstance(it.get("answer_key"), dict) else {}
        mode = str((ak or {}).get("mode") or "").strip()
        rec = it.get("reconciliation") if isinstance(it.get("reconciliation"), dict) else {}
        status = str((rec or {}).get("status") or "").strip()
        if mode != "none" and status != "blocked":
            continue
        missing_qns.append(qn)
        entry = answer_map.get(qn)
        if not entry:
            continue
        emode = str(entry.get("mode") or "").strip()
        value = entry.get("value")
        if emode in {"single_choice", "short_answer"} and str(value or "").strip():
            fillable_qns.append(qn)
        elif emode == "boolean_group" and isinstance(value, dict) and value:
            fillable_qns.append(qn)

    missing_set = sorted(set(missing_qns))
    fillable_set = sorted(set(fillable_qns))
    return {
        "missing_question_numbers": missing_set,
        "fillable_question_numbers": fillable_set,
        "missing_count": len(missing_set),
        "fillable_count": len(fillable_set),
    }


def _classify_bundle(bundle: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Returns: (category, why, smallest_unlock_path)
    """
    if int(bundle.get("question_count", 0) or 0) <= 0:
        return (
            "blocked_by_other",
            "bundle has zero questions",
            "Re-run conversion/segmentation; do not approve/import zero-question bundles.",
        )
    if int(bundle.get("conflict_count", 0) or 0) > 0:
        return (
            "blocked_by_real_conflict",
            f"bundle has conflict_count={int(bundle.get('conflict_count', 0) or 0)}",
            "Manual review required to resolve conflicts; cannot auto-approve.",
        )

    rubric_gap = int(bundle.get("rubric_gap_count", 0) or 0)
    doc_family = str(bundle.get("document_family") or "")
    if rubric_gap > 0 and doc_family == "rubric_scoring_doc":
        return (
            "blocked_by_rubric_attachment",
            f"rubric_scoring_doc has rubric_gap_count={rubric_gap}",
            "Requires rubric attachment improvements (table rubric markers) or manual rubric entry during review.",
        )

    missing = int(bundle.get("missing_answer_count", 0) or 0)
    fillable = int(bundle.get("missing_fillable_via_answer_summary", {}).get("fillable_count", 0) or 0)
    missing_count = int(bundle.get("missing_fillable_via_answer_summary", {}).get("missing_count", 0) or 0)

    if missing > 0:
        if missing_count > 0 and missing_count == fillable:
            return (
                "workflow_unlockable_now",
                "all missing answers are explicitly fillable via extracted answer_summary entries",
                "Use review UI filters for missing answers, apply explicit answer_summary overrides, finalize, then import in approved-only mode.",
            )
        return (
            "blocked_by_missing_answer_extraction",
            f"missing_answer_count={missing} but only {fillable}/{max(1, missing_count)} missing questions are explicitly covered by answer_summary",
            "Requires upstream answer extraction (end key / inline-solution parsing) or substantial manual review; not workflow-only.",
        )

    required_pending = int(bundle.get("required_pending_count", 0) or 0)
    if required_pending > 0:
        if rubric_gap > 0:
            return (
                "blocked_by_rubric_attachment",
                f"rubric_gap_count={rubric_gap}",
                "Manual rubric entry in review or upstream rubric extraction improvements.",
            )
        return (
            "blocked_by_other",
            f"required_pending_count={required_pending} but missing_answer_count=0; see issue_codes",
            "Inspect issue_codes and fix via review overrides where evidence is explicit; otherwise upstream work needed.",
        )

    return (
        "workflow_unlockable_now",
        "no required_pending and no detected conflicts",
        "Finalize and import approved-only (should be approveable).",
    )


def _render_md(matrix: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Coverage Unlock Matrix")
    lines.append("")
    lines.append(f"- created_at: `{matrix.get('created_at','')}`")
    lines.append(f"- contracts_root: `{matrix.get('contracts_root','')}`")
    lines.append("")

    lines.append("## Summary")
    counts = matrix.get("category_counts", {}) if isinstance(matrix.get("category_counts"), dict) else {}
    lines.append(f"- category_counts: `{counts}`")
    lines.append("")

    lines.append("## Matrix")
    lines.append("| bundle | subject | family | required_pending | conflicts | missing_answer | rubric_gaps | category |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
    for row in matrix.get("bundles", []) or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| {name} | {subject} | {family} | {req} | {conf} | {miss} | {rub} | {cat} |".format(
                name=str(row.get("bundle_name", "")),
                subject=str(row.get("subject", "")),
                family=str(row.get("document_family", "")),
                req=int(row.get("required_pending_count", 0) or 0),
                conf=int(row.get("conflict_count", 0) or 0),
                miss=int(row.get("missing_answer_count", 0) or 0),
                rub=int(row.get("rubric_gap_count", 0) or 0),
                cat=str(row.get("category", "")),
            )
        )
    lines.append("")

    lines.append("## Recommended Order Of Attack")
    for entry in matrix.get("recommended_order", []) or []:
        if not isinstance(entry, dict):
            continue
        lines.append(f"- `{entry.get('bundle_name','')}`: {entry.get('reason','')}")
    lines.append("")

    lines.append("## Explicit Lists")
    for key in ["unlockable_now", "requires_parser_work", "requires_rubric_work", "requires_conflict_review", "blocked_other"]:
        lines.append(f"### {key}")
        for name in matrix.get("lists", {}).get(key, []) if isinstance(matrix.get("lists", {}), dict) else []:
            lines.append(f"- `{name}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


@dataclass
class BundleRow:
    bundle_name: str
    bundle_id: str
    bundle_path: str
    subject: str
    question_count: int
    required_pending_count: int
    secondary_pending_count: int
    conflict_count: int
    issue_codes: List[str]
    document_family: str
    document_family_confidence: float
    publish_verdict: str
    answer_summary_present: bool
    answer_summary_entry_count: int
    missing_answer_count: int
    unresolved_reconciliation_count: int
    rubric_gap_count: int
    missing_fillable_via_answer_summary: Dict[str, Any]
    category: str
    why: str
    smallest_unlock_path: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "bundle_name": self.bundle_name,
            "bundle_id": self.bundle_id,
            "bundle_path": self.bundle_path,
            "subject": self.subject,
            "question_count": self.question_count,
            "required_pending_count": self.required_pending_count,
            "secondary_pending_count": self.secondary_pending_count,
            "conflict_count": self.conflict_count,
            "issue_codes": self.issue_codes,
            "document_family": self.document_family,
            "document_family_confidence": self.document_family_confidence,
            "publish_verdict": self.publish_verdict,
            "answer_summary_present": self.answer_summary_present,
            "answer_summary_entry_count": self.answer_summary_entry_count,
            "missing_answer_count": self.missing_answer_count,
            "unresolved_reconciliation_count": self.unresolved_reconciliation_count,
            "rubric_gap_count": self.rubric_gap_count,
            "missing_fillable_via_answer_summary": self.missing_fillable_via_answer_summary,
            "category": self.category,
            "why": self.why,
            "smallest_unlock_path": self.smallest_unlock_path,
        }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a coverage unlock matrix for approved coverage expansion (planning/reporting only).")
    parser.add_argument("--contracts-root", type=Path, default=DEFAULT_CONTRACTS_ROOT, help="Root containing bundle contract dirs")
    parser.add_argument("--jar", type=Path, default=None, help="Path to built jar (review-server)")
    parser.add_argument("--output-parent", type=Path, default=DEFAULT_OUTPUT_PARENT, help="Output parent directory")
    args = parser.parse_args(argv)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_root = (args.output_parent / f"{DEFAULT_PREFIX}-{ts}").resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    rows: List[BundleRow] = []
    by_name: Dict[str, Path] = {p.name: p for p in _discover_bundle_dirs(args.contracts_root.resolve())}
    for bundle_name, bundle_dir in sorted(by_name.items(), key=lambda kv: kv[0]):

        manifest = _read_json(bundle_dir / "manifest.json")
        qb = _read_json(bundle_dir / "question_bank_items.json")
        exam = _read_json(bundle_dir / "exam_bundle.json")
        parser_report = _read_json(bundle_dir / "parser_report.json")

        ans_map = _answer_summary_map(exam)
        missing_counts = _count_unresolved_items(qb)
        fillable = _missing_fillable_via_answer_summary(qb, ans_map)

        summary = exam.get("summary") if isinstance(exam.get("summary"), dict) else {}
        doc_family = str((parser_report.get("summary") or {}).get("document_family") or qb.get("document_family") or "unknown")
        doc_family_conf = float((parser_report.get("summary") or {}).get("document_family_confidence") or 0.0)

        items = qb.get("items") or []
        required_pending = 0
        secondary_pending = 0
        conflict_item_count = 0
        all_issue_codes: List[str] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            ak = it.get("answer_key") if isinstance(it.get("answer_key"), dict) else {}
            mode = str((ak or {}).get("mode") or "").strip()
            rec = it.get("reconciliation") if isinstance(it.get("reconciliation"), dict) else {}
            status = str((rec or {}).get("status") or "").strip()
            qtype = str(it.get("question_type") or "").strip()
            parse_conf = float(it.get("parse_confidence") or 0.0)

            issue_codes = set()
            for code in (it.get("qa_flags") or []):
                issue_codes.add(str(code))
            for code in (it.get("parser_warning_codes") or []):
                issue_codes.add(str(code))
            if status == "blocked":
                issue_codes.add("canonical_answer_missing")
            elif status == "conflict":
                issue_codes.add("answer_source_conflict")
                issue_codes.add("unresolved_reconciliation")
            elif status == "needs_review":
                issue_codes.add("unresolved_reconciliation")
            if qtype == "essay" and mode == "none":
                issue_codes.add("missing_rubric_source")
            if parse_conf > 0.0 and parse_conf < 0.6:
                issue_codes.add("low_parse_confidence")
            if not status and mode == "none":
                issue_codes.add("canonical_answer_missing")
            if doc_family == "unknown":
                issue_codes.add("document_family_ambiguous")

            required = bool(issue_codes.intersection(REQUIRED_TRIGGER_CODES) or status in {"needs_review", "conflict"})
            secondary = bool(issue_codes.intersection(SECONDARY_TRIGGER_CODES))
            if required:
                required_pending += 1
            if secondary and not required:
                secondary_pending += 1
            if status == "conflict" or "answer_source_conflict" in issue_codes:
                conflict_item_count += 1
            all_issue_codes.extend(sorted(issue_codes))

        # Bundle-level issue_codes: de-dupe and keep short list for reporting.
        issue_codes_sorted = sorted(set(all_issue_codes))

        row: Dict[str, Any] = {
            "bundle_name": bundle_name,
            "bundle_id": str(manifest.get("bundle_id") or ""),
            "bundle_path": str(bundle_dir.resolve()),
            "subject": str(qb.get("subject") or manifest.get("subject") or "generic"),
            "question_count": int(qb.get("item_count") or len(items)),
            "required_pending_count": required_pending,
            "secondary_pending_count": secondary_pending,
            "conflict_count": conflict_item_count,
            "issue_codes": issue_codes_sorted,
            "document_family": doc_family,
            "document_family_confidence": doc_family_conf,
            "publish_verdict": str(summary.get("publish_verdict") or ""),
            "answer_summary_present": bool((exam.get("answer_summary") or {}).get("present") is True),
            "answer_summary_entry_count": len(ans_map),
            "missing_fillable_via_answer_summary": fillable,
            **missing_counts,
        }
        category, why, unlock_path = _classify_bundle({**row, **missing_counts})
        rows.append(
            BundleRow(
                bundle_name=bundle_name,
                bundle_id=row["bundle_id"],
                bundle_path=row["bundle_path"],
                subject=row["subject"],
                question_count=row["question_count"],
                required_pending_count=row["required_pending_count"],
                secondary_pending_count=row["secondary_pending_count"],
                conflict_count=row["conflict_count"],
                issue_codes=row["issue_codes"],
                document_family=row["document_family"],
                document_family_confidence=row["document_family_confidence"],
                publish_verdict=row["publish_verdict"],
                answer_summary_present=row["answer_summary_present"],
                answer_summary_entry_count=row["answer_summary_entry_count"],
                missing_answer_count=row["missing_answer_count"],
                unresolved_reconciliation_count=row["unresolved_reconciliation_count"],
                rubric_gap_count=row["rubric_gap_count"],
                missing_fillable_via_answer_summary=row["missing_fillable_via_answer_summary"],
                category=category,
                why=why,
                smallest_unlock_path=unlock_path,
            )
        )

    rows.sort(key=lambda r: (r.category, -r.required_pending_count, r.bundle_name))
    category_counts: Dict[str, int] = {}
    lists = {
        "unlockable_now": [],
        "requires_parser_work": [],
        "requires_rubric_work": [],
        "requires_conflict_review": [],
        "blocked_other": [],
    }
    for r in rows:
        category_counts[r.category] = category_counts.get(r.category, 0) + 1
        if r.category == "workflow_unlockable_now":
            lists["unlockable_now"].append(r.bundle_name)
        elif r.category == "blocked_by_missing_answer_extraction":
            lists["requires_parser_work"].append(r.bundle_name)
        elif r.category == "blocked_by_rubric_attachment":
            lists["requires_rubric_work"].append(r.bundle_name)
        elif r.category == "blocked_by_real_conflict":
            lists["requires_conflict_review"].append(r.bundle_name)
        else:
            lists["blocked_other"].append(r.bundle_name)

    # Recommended order: unlockable now first, then conflict review, then rubric, then parser-heavy.
    recommended_order: List[Dict[str, str]] = []
    for r in rows:
        if r.category == "workflow_unlockable_now":
            recommended_order.append({"bundle_name": r.bundle_name, "reason": r.smallest_unlock_path})
    for r in rows:
        if r.category == "blocked_by_real_conflict":
            recommended_order.append({"bundle_name": r.bundle_name, "reason": r.smallest_unlock_path})
    for r in rows:
        if r.category == "blocked_by_rubric_attachment":
            recommended_order.append({"bundle_name": r.bundle_name, "reason": r.smallest_unlock_path})
    for r in rows:
        if r.category == "blocked_by_missing_answer_extraction":
            recommended_order.append({"bundle_name": r.bundle_name, "reason": r.smallest_unlock_path})
    for r in rows:
        if r.category == "blocked_by_other":
            recommended_order.append({"bundle_name": r.bundle_name, "reason": r.smallest_unlock_path})

    matrix: Dict[str, Any] = {
        "schema_version": "coverage_unlock_matrix.v1",
        "created_at": _now_iso(),
        "contracts_root": str(args.contracts_root.resolve()),
        "bundles": [r.as_dict() for r in rows],
        "category_counts": category_counts,
        "lists": lists,
        "recommended_order": recommended_order,
    }

    out_json = output_root / "coverage_unlock_matrix.json"
    out_md = output_root / "coverage_unlock_matrix.md"
    _write_text(out_json, _json(matrix) + "\n")
    _write_text(out_md, _render_md(matrix))

    print(_json({"output_root": str(output_root), "json": str(out_json), "md": str(out_md)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
