from __future__ import annotations

import argparse
import json
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.export.docx_exporter import ExportIssue, MinimalDocxBuilder

REPORT_SCHEMA_VERSION = "assembled_exam_docx_export_report.v1"
REPORT_ARTIFACT_TYPE = "assembled_exam_docx_export_report"

ASSEMBLY_SCHEMA_VERSION = "question_bank_exam_assembly.v1"
ASSEMBLY_ARTIFACT_TYPE = "exam_assembly"


@dataclass
class AssembledExamExportError(Exception):
    stage: str
    code: str
    message: str
    details: Dict[str, Any]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.stage}:{self.code}: {self.message}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _add_issue(
    issues: List[ExportIssue],
    *,
    code: str,
    severity: str,
    message: str,
    item_id: str = "",
    location: str = "",
) -> None:
    issues.append(
        ExportIssue(
            code=code,
            severity=severity,
            message=message,
            exam_id="",
            question_id=item_id,
            location=location,
        )
    )


def _is_blocker(issue: ExportIssue) -> bool:
    return str(issue.severity or "").strip().lower() == "blocker"


def _is_warning(issue: ExportIssue) -> bool:
    return str(issue.severity or "").strip().lower() in {"warning", "error"}


def _final_verdict(issues: List[ExportIssue]) -> Tuple[str, int, int]:
    warning_count = sum(1 for issue in issues if _is_warning(issue))
    blocker_count = sum(1 for issue in issues if _is_blocker(issue))
    if blocker_count > 0:
        return ("blocked", warning_count, blocker_count)
    if warning_count > 0:
        return ("needs_review", warning_count, blocker_count)
    return ("safe_to_export", warning_count, blocker_count)


def _load_json_object(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssembledExamExportError("load", "invalid_json_root", "artifact must be a JSON object", {"path": str(path)})
    return payload


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:  # noqa: BLE001
        return default


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _rubric_text(item: Dict[str, Any]) -> str:
    rubric = item.get("rubric", {}) if isinstance(item.get("rubric"), dict) else {}
    text = _scalar_text(rubric.get("rubric_text"))
    if text:
        return text
    rubric_json = rubric.get("rubric_json")
    if isinstance(rubric_json, dict):
        return _scalar_text(rubric_json.get("rubric_text"))
    return ""


def _answer_render_lines(item: Dict[str, Any]) -> List[str]:
    answer_key = item.get("answer_key", {}) if isinstance(item.get("answer_key"), dict) else {}
    mode = _scalar_text(answer_key.get("mode"))
    value = answer_key.get("value")
    accepted_answers = answer_key.get("accepted_answers")
    subanswers = answer_key.get("subanswers")

    def _bool_text(val: Any) -> str:
        if isinstance(val, bool):
            return "Đúng" if val else "Sai"
        return _scalar_text(val)

    def _extract_short_answer() -> str:
        direct = _scalar_text(value)
        if direct:
            return direct
        if isinstance(accepted_answers, list):
            picks: List[str] = []
            for entry in accepted_answers:
                if isinstance(entry, dict):
                    cand = _scalar_text(entry.get("normalized")) or _scalar_text(entry.get("raw"))
                else:
                    cand = _scalar_text(entry)
                if cand:
                    picks.append(cand)
            seen = set()
            uniq = [p for p in picks if not (p in seen or seen.add(p))]
            return " / ".join(uniq)
        if isinstance(accepted_answers, dict):
            return _scalar_text(accepted_answers.get("normalized")) or _scalar_text(accepted_answers.get("raw"))
        return ""

    def _extract_boolean_payload() -> Any:
        if value is not None:
            return value
        return subanswers

    if not mode or mode in {"none", "rubric"}:
        return ["n/a"]
    if mode == "single_choice":
        choice = _scalar_text(value)
        if not choice:
            return ["n/a"]
        return [f"Đáp án: {choice}"]
    if mode == "short_answer":
        short_answer = _extract_short_answer()
        if not short_answer:
            return ["n/a"]
        return [f"Đáp án: {short_answer}"]
    if mode == "boolean_group":
        payload = _extract_boolean_payload()
        if isinstance(payload, dict):
            lines = ["Đáp án:"]
            for key in sorted(payload.keys(), key=lambda entry: str(entry)):
                lines.append(f"- {key}: {_bool_text(payload.get(key)) or '?'}")
            return lines
        if isinstance(payload, list):
            lines = ["Đáp án:"]
            for idx, row in enumerate(payload, start=1):
                if isinstance(row, dict):
                    label = row.get("label") or row.get("key") or row.get("id") or idx
                    row_value = row.get("value")
                    lines.append(f"- {label}: {_bool_text(row_value) or '?'}")
                else:
                    lines.append(f"- {idx}: {_bool_text(row) or '?'}")
            return lines
        scalar = _bool_text(payload)
        if not scalar:
            return ["n/a"]
        return [f"Đáp án: {scalar}"]
    if mode == "essay":
        return ["Essay: see rubric."]
    other = _scalar_text(value)
    if not other:
        return ["n/a"]
    return [f"{mode}: {other}"]


def _question_content(item: Dict[str, Any]) -> str:
    for key in ["prompt_preview", "question_content", "stem", "content_text", "content_preview"]:
        text = _scalar_text(item.get(key))
        if text:
            return text
    return ""


def _validate_assembly_artifact(artifact: Dict[str, Any]) -> List[ExportIssue]:
    issues: List[ExportIssue] = []
    schema_version = _scalar_text(artifact.get("schema_version"))
    artifact_type = _scalar_text(artifact.get("artifact_type"))
    if schema_version != ASSEMBLY_SCHEMA_VERSION:
        _add_issue(
            issues,
            code="unsupported_schema_version",
            severity="blocker",
            message=f"unsupported schema_version: {schema_version!r} (expected {ASSEMBLY_SCHEMA_VERSION!r})",
            location="schema_version",
        )
    if artifact_type != ASSEMBLY_ARTIFACT_TYPE:
        _add_issue(
            issues,
            code="unsupported_artifact_type",
            severity="blocker",
            message=f"unsupported artifact_type: {artifact_type!r} (expected {ASSEMBLY_ARTIFACT_TYPE!r})",
            location="artifact_type",
        )
    if not _scalar_text(artifact.get("assembly_id")):
        _add_issue(
            issues,
            code="missing_assembly_id",
            severity="blocker",
            message="missing assembly_id",
            location="assembly_id",
        )
    if _scalar_text(artifact.get("assembly_mode")) not in {"fixed", "random"}:
        _add_issue(
            issues,
            code="invalid_assembly_mode",
            severity="blocker",
            message=f"invalid assembly_mode: {_scalar_text(artifact.get('assembly_mode'))!r}",
            location="assembly_mode",
        )

    exam = artifact.get("exam", {}) if isinstance(artifact.get("exam"), dict) else {}
    for key in ["exam_id", "title", "subject"]:
        if not _scalar_text(exam.get(key)):
            _add_issue(
                issues,
                code=f"missing_exam_{key}",
                severity="blocker",
                message=f"missing exam.{key}",
                location=f"exam.{key}",
            )

    items = artifact.get("items")
    if not isinstance(items, list):
        _add_issue(
            issues,
            code="items_not_a_list",
            severity="blocker",
            message="items must be a list",
            location="items",
        )
        return issues
    if len(items) == 0:
        _add_issue(
            issues,
            code="items_empty",
            severity="blocker",
            message="items list is empty; nothing to export",
            location="items",
        )
        return issues

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            _add_issue(
                issues,
                code="item_not_an_object",
                severity="blocker",
                message=f"items[{idx}] must be a JSON object",
                location=f"items[{idx}]",
            )
            continue
        item_id = _scalar_text(item.get("item_id"))
        if not item_id:
            _add_issue(
                issues,
                code="missing_item_id",
                severity="blocker",
                message=f"missing item_id for items[{idx}]",
                location=f"items[{idx}].item_id",
            )
        if not _scalar_text(item.get("bundle_id")):
            _add_issue(
                issues,
                code="missing_bundle_id",
                severity="blocker",
                message=f"missing bundle_id for items[{idx}]",
                item_id=item_id,
                location=f"items[{idx}].bundle_id",
            )
        if not _scalar_text(item.get("question_type")):
            _add_issue(
                issues,
                code="missing_question_type",
                severity="blocker",
                message=f"missing question_type for items[{idx}]",
                item_id=item_id,
                location=f"items[{idx}].question_type",
            )
        content = _question_content(item)
        if not content:
            _add_issue(
                issues,
                code="missing_question_content",
                severity="blocker",
                message=f"missing question content fields for items[{idx}] (expected prompt_preview at minimum)",
                item_id=item_id,
                location=f"items[{idx}]",
            )
        question_number = _safe_int(item.get("question_number"), 0)
        if question_number <= 0:
            _add_issue(
                issues,
                code="invalid_question_number",
                severity="warning",
                message=f"invalid question_number for items[{idx}]; will fall back to selection_index+1",
                item_id=item_id,
                location=f"items[{idx}].question_number",
            )
        selection_index = _safe_int(item.get("selection_index"), -1)
        if selection_index < 0:
            _add_issue(
                issues,
                code="invalid_selection_index",
                severity="warning",
                message=f"invalid selection_index for items[{idx}]; order may be unstable",
                item_id=item_id,
                location=f"items[{idx}].selection_index",
            )
    return issues


def _write_multiline_text(builder: MinimalDocxBuilder, paragraph: Any, text: str) -> None:
    lines = (text or "").splitlines()
    if not lines:
        builder.add_text_run(paragraph, "n/a")
        return
    for idx, line in enumerate(lines):
        if idx > 0:
            builder.add_break(paragraph)
        builder.add_text_run(paragraph, line)


def export_exam_assembly_to_docx(
    assembly_artifact_path: str | Path,
    output_docx_path: str | Path,
    *,
    mode: str,
    report_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    artifact_path = Path(assembly_artifact_path).resolve()
    output_docx = Path(output_docx_path).resolve()
    output_report = Path(report_path).resolve() if report_path else output_docx.with_name("assembled_exam_docx_export_report.json")

    issues: List[ExportIssue] = []
    export_view = "teacher_docx" if mode == "teacher" else "student_docx"

    try:
        artifact = _load_json_object(artifact_path)
    except AssembledExamExportError as ex:
        issues.append(ExportIssue(code=ex.code, severity="blocker", message=ex.message, location=str(ex.details.get("path", ""))))
        artifact = {}
    except (OSError, json.JSONDecodeError) as ex:
        issues.append(ExportIssue(code="assembly_artifact_read_failed", severity="blocker", message=str(ex), location=str(artifact_path)))
        artifact = {}

    if artifact:
        issues.extend(_validate_assembly_artifact(artifact))

    exam = artifact.get("exam", {}) if isinstance(artifact.get("exam"), dict) else {}
    items = artifact.get("items", []) if isinstance(artifact.get("items"), list) else []

    shown_answer_count = 0
    shown_rubric_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if mode == "teacher":
            answer_lines = _answer_render_lines(item)
            if answer_lines and answer_lines != ["n/a"]:
                shown_answer_count += 1
            if _rubric_text(item):
                shown_rubric_count += 1

    t1 = time.perf_counter()
    verdict, warnings_count, blockers_count = _final_verdict(issues)

    report: Dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "artifact_type": REPORT_ARTIFACT_TYPE,
        "input_assembly_artifact_path": str(artifact_path),
        "output_docx_path": str(output_docx),
        "output_report_path": str(output_report),
        "export_view": export_view,
        "mode": mode,
        "assembly_id": _scalar_text(artifact.get("assembly_id")),
        "assembly_mode": _scalar_text(artifact.get("assembly_mode")),
        "exam": {
            "exam_id": _scalar_text(exam.get("exam_id")),
            "title": _scalar_text(exam.get("title")),
            "subject": _scalar_text(exam.get("subject")),
        },
        "metrics": {
            "item_count": len(items) if isinstance(items, list) else 0,
            "shown_answer_count": shown_answer_count,
            "shown_rubric_count": shown_rubric_count,
        },
        "issues": [issue.as_dict() for issue in issues],
        "warnings_count": warnings_count,
        "blockers_count": blockers_count,
        "verdict": verdict,
        "timings": {
            "load_and_validate_ms": round((t1 - t0) * 1000.0, 3),
            "build_docx_ms": 0.0,
            "zip_integrity_ms": 0.0,
        },
    }

    if verdict == "blocked":
        output_report.parent.mkdir(parents=True, exist_ok=True)
        output_report.write_text(_json(report) + "\n", encoding="utf-8")
        return report

    build_t0 = time.perf_counter()
    builder = MinimalDocxBuilder(issues=issues)

    title = _scalar_text(exam.get("title")) or "Assembled Exam"
    p_title = builder.add_paragraph(style="Heading1")
    builder.add_text_run(p_title, title)

    p_meta = builder.add_paragraph()
    builder.add_text_run(
        p_meta,
        f"Assembled exam DOCX export ({export_view}) | assembly_id={_scalar_text(artifact.get('assembly_id'))} | mode={_scalar_text(artifact.get('assembly_mode'))} | subject={_scalar_text(exam.get('subject'))}",
    )

    ordered_items = [item for item in items if isinstance(item, dict)]
    ordered_items.sort(key=lambda it: _safe_int(it.get("selection_index"), 10_000_000))

    for idx, item in enumerate(ordered_items):
        item_id = _scalar_text(item.get("item_id"))
        question_number = _safe_int(item.get("question_number"), 0)
        if question_number <= 0:
            question_number = idx + 1

        question_type = _scalar_text(item.get("question_type"))
        header = f"Câu {question_number}."
        if question_type:
            header = f"{header} ({question_type})"
        p_q = builder.add_paragraph(style="Heading2")
        builder.add_text_run(p_q, header, bold=True)

        content = _question_content(item)
        p_content = builder.add_paragraph()
        _write_multiline_text(builder, p_content, content)

        if mode == "teacher":
            reconciliation = item.get("reconciliation", {}) if isinstance(item.get("reconciliation"), dict) else {}
            rec_status = _scalar_text(reconciliation.get("status"))
            if rec_status in {"conflict", "blocked", "needs_review"}:
                _add_issue(
                    issues,
                    code="reconciliation_not_resolved",
                    severity="warning",
                    message=f"item reconciliation status is {rec_status}",
                    item_id=item_id,
                    location=f"item:{item_id}",
                )

            p_rec = builder.add_paragraph()
            builder.add_text_run(p_rec, "Reconciliation: ", bold=True)
            builder.add_text_run(p_rec, rec_status or "n/a")

            p_ans = builder.add_paragraph()
            builder.add_text_run(p_ans, "Đáp án:", bold=True)
            answer_lines = _answer_render_lines(item)
            if answer_lines:
                first = answer_lines[0].strip()
                if first and first.lower().startswith("đáp án"):
                    pieces = first.split(":", 1)
                    if len(pieces) == 2 and pieces[1].strip():
                        builder.add_text_run(p_ans, " " + pieces[1].strip())
                else:
                    builder.add_text_run(p_ans, " " + first)
                for extra in answer_lines[1:]:
                    builder.add_break(p_ans)
                    builder.add_text_run(p_ans, extra)
            else:
                builder.add_text_run(p_ans, " n/a")

            rubric_text = _rubric_text(item)
            p_rubric = builder.add_paragraph()
            builder.add_text_run(p_rubric, "Rubric: ", bold=True)
            if rubric_text:
                _write_multiline_text(builder, p_rubric, rubric_text)
            else:
                builder.add_text_run(p_rubric, "n/a")

            p_prov = builder.add_paragraph()
            builder.add_text_run(p_prov, "Provenance: ", bold=True)
            prov_bits = [
                f"bundle_id={_scalar_text(item.get('bundle_id'))}",
                f"item_id={item_id}",
                f"approved_source={_scalar_text(item.get('approved_source'))}",
                f"import_mode={_scalar_text(item.get('import_mode'))}",
                f"import_readiness={_scalar_text(item.get('import_readiness'))}",
                f"imported_at={_scalar_text(item.get('imported_at'))}",
            ]
            builder.add_text_run(p_prov, " | ".join(bit for bit in prov_bits if bit and not bit.endswith("=")))

    try:
        builder.write_docx(output_docx)
    except Exception as ex:  # noqa: BLE001
        _add_issue(
            issues,
            code="docx_package_failed",
            severity="blocker",
            message=f"Failed to package DOCX output: {ex}",
            location=str(output_docx),
        )

    build_t1 = time.perf_counter()
    report["timings"]["build_docx_ms"] = round((build_t1 - build_t0) * 1000.0, 3)

    zip_t0 = time.perf_counter()
    if output_docx.exists():
        try:
            with zipfile.ZipFile(output_docx, "r") as zf:
                bad = zf.testzip()
                if bad:
                    _add_issue(
                        issues,
                        code="docx_zip_integrity_failed",
                        severity="blocker",
                        message=f"zip integrity check failed; first bad file: {bad}",
                        location=str(output_docx),
                    )
        except Exception as ex:  # noqa: BLE001
            _add_issue(
                issues,
                code="docx_zip_integrity_failed",
                severity="blocker",
                message=f"zip integrity check failed: {ex}",
                location=str(output_docx),
            )
    else:
        _add_issue(
            issues,
            code="docx_missing_after_write",
            severity="blocker",
            message="DOCX output file was not created",
            location=str(output_docx),
        )
    zip_t1 = time.perf_counter()
    report["timings"]["zip_integrity_ms"] = round((zip_t1 - zip_t0) * 1000.0, 3)

    verdict, warnings_count, blockers_count = _final_verdict(issues)
    report["issues"] = [issue.as_dict() for issue in issues]
    report["warnings_count"] = warnings_count
    report["blockers_count"] = blockers_count
    report["verdict"] = verdict

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(_json(report) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export an assembled exam artifact JSON to a preview-grade DOCX.")
    parser.add_argument("--artifact", type=Path, default=None, help="Path to assembled exam JSON artifact")
    parser.add_argument("--assembly-id", type=str, default=None, help="Resolve a persisted assembly record by assembly_id")
    parser.add_argument("--db", type=Path, default=None, help="SQLite approved-import boundary DB (when using --assembly-id)")
    parser.add_argument("--db-url", type=str, default=None, help="Postgres URL (when using --assembly-id; or QB_DB_URL/DATABASE_URL)")
    parser.add_argument("--mode", type=str, required=True, choices=["student", "teacher"], help="Export view mode")
    parser.add_argument("--output-docx", type=Path, required=True, help="Output .docx path")
    parser.add_argument("--report", type=Path, default=None, help="Optional export report output path")
    args = parser.parse_args(argv)

    if bool(args.artifact) == bool(args.assembly_id):
        raise SystemExit("provide exactly one of --artifact or --assembly-id")

    if args.assembly_id:
        from .exam_assembly import resolve_persisted_assembly_artifact_path

        artifact_path = resolve_persisted_assembly_artifact_path(
            assembly_id=str(args.assembly_id),
            db_path=(args.db.resolve() if args.db else None),
            db_url=args.db_url,
        )
    else:
        artifact_path = args.artifact.resolve()

    report = export_exam_assembly_to_docx(
        artifact_path,
        args.output_docx,
        mode=args.mode,
        report_path=args.report,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("verdict") != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
