#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, inspect_docx, read_json

DEFAULT_OUTPUT = ROOT / "regression_set" / "modern_docx_omml_promotion_preflight_report.json"
DOCUMENT_XML = "word/document.xml"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _is_word(element: ElementTree.Element, local_name: str) -> bool:
    return _namespace(element.tag) == WORD_NS and _local_name(element.tag) == local_name


def _to_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _is_git_tracked(path: Path) -> bool:
    rel = _to_rel(path)
    if rel.startswith("/"):
        return False
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _object_counts(path: Path) -> Dict[str, int]:
    out = {"w_object_count": 0, "object_like_tag_count": 0}
    try:
        with zipfile.ZipFile(path) as docx:
            if DOCUMENT_XML not in docx.namelist():
                return out
            data = docx.read(DOCUMENT_XML)
    except (OSError, zipfile.BadZipFile):
        return out

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return out

    for element in root.iter():
        name = _local_name(element.tag)
        if _is_word(element, "object"):
            out["w_object_count"] += 1
        if name in {"object", "OLEObject"}:
            out["object_like_tag_count"] += 1
    return out


def _shape_family(inline_count: int, block_count: int) -> str:
    if inline_count > 0 and block_count > 0:
        return "mixed_inline_block"
    if inline_count > 0:
        return "inline_only"
    if block_count > 0:
        return "block_only"
    return "no_omml"


def _load_local_only_candidates(inventory_path: Path) -> List[Dict[str, Any]]:
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list):
        return []

    out: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        if str(case.get("status", "")).strip() != "local_only":
            continue
        if str(case.get("classification", "")).strip() != "supported":
            continue
        source = str(case.get("source_docx", "")).strip()
        if not source:
            continue
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = (ROOT / source_path).resolve()
        out.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "source_docx": source,
                "source_path": source_path,
            }
        )
    return out


def _evaluate_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    path = candidate["source_path"]
    inspection = inspect_docx(path)
    object_counts = _object_counts(path)

    omath_count = int(inspection.get("omath_count", 0) or 0)
    inline_count = int(inspection.get("inline_omath_count", 0) or 0)
    block_count = int(inspection.get("omathpara_count", 0) or 0)
    object_like_count = int(object_counts.get("object_like_tag_count", 0) or 0)

    parseable = bool(inspection.get("document_xml_parseable"))
    native_omml_present = bool(inspection.get("basic_omml_structure_present"))
    shape_family = _shape_family(inline_count, block_count)

    structurally_suitable = parseable and native_omml_present and object_like_count > 0

    size_bytes = path.stat().st_size if path.exists() else -1
    ci_safe = structurally_suitable and size_bytes <= 1_000_000 and (omath_count + block_count) <= 50 and object_like_count <= 600

    git_tracked = _is_git_tracked(path)
    repo_trackable = git_tracked

    if shape_family == "mixed_inline_block" and structurally_suitable:
        confidence_gain = "high"
    elif structurally_suitable:
        confidence_gain = "medium"
    else:
        confidence_gain = "low"

    blockers: List[str] = []
    if not structurally_suitable:
        blockers.append("not structurally suitable for mixed object+OMML promotion")
    if not ci_safe:
        blockers.append("not CI-safe under current practical size/complexity preflight thresholds")
    if not repo_trackable:
        blockers.append("not currently repo-tracked (provenance/legal trackability unresolved)")

    if structurally_suitable and ci_safe and repo_trackable and confidence_gain in {"high", "medium"}:
        decision = "eligible_for_repo_promotion"
        recommended_next_action = "promote into active repo-tracked fixture scope in a dedicated promotion checkpoint"
    else:
        decision = "keep_local_only"
        if repo_trackable:
            recommended_next_action = "retain as local-only until CI-safe constraints and confidence gain criteria are simultaneously met"
        else:
            recommended_next_action = "retain local-only; first clear provenance/legal trackability, then re-run preflight"

    return {
        "case_id": candidate["case_id"],
        "candidate": _to_rel(path),
        "structural": {
            "suitable": structurally_suitable,
            "shape_family": shape_family,
            "native_omml_present": native_omml_present,
            "omath_count": omath_count,
            "inline_omath_count": inline_count,
            "omathpara_count": block_count,
            "object_like_tag_count": object_like_count,
            "document_xml_parseable": parseable,
        },
        "ci_safe": ci_safe,
        "repo_trackable": repo_trackable,
        "confidence_gain_if_promoted": confidence_gain,
        "blockers": blockers,
        "decision": decision,
        "recommended_next_action": recommended_next_action,
        "metrics": {
            "size_bytes": size_bytes,
            "git_tracked": git_tracked,
        },
    }


def _best_mixed_candidate(items: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    mixed = [item for item in items if item["structural"]["shape_family"] == "mixed_inline_block"]
    if not mixed:
        return None
    mixed.sort(
        key=lambda item: (
            1 if item["decision"] == "eligible_for_repo_promotion" else 0,
            1 if item["ci_safe"] else 0,
            item["structural"]["omath_count"] + item["structural"]["omathpara_count"],
            -item["metrics"]["size_bytes"],
        ),
        reverse=True,
    )
    return mixed[0]


def build_report(inventory_path: Path) -> Dict[str, Any]:
    candidates = _load_local_only_candidates(inventory_path)
    evaluations = [_evaluate_candidate(candidate) for candidate in candidates]

    best_mixed = _best_mixed_candidate(evaluations)
    if best_mixed is None:
        overall = {
            "best_mixed_candidate": None,
            "stop_condition": "no local-only mixed candidate available",
            "summary_decision": "stop_with_preflight_only",
        }
    elif best_mixed["decision"] != "eligible_for_repo_promotion":
        overall = {
            "best_mixed_candidate": best_mixed["case_id"],
            "stop_condition": "best local-only mixed candidate still fails promotion preflight",
            "summary_decision": "stop_with_preflight_only",
        }
    else:
        overall = {
            "best_mixed_candidate": best_mixed["case_id"],
            "stop_condition": "promotion preflight passed",
            "summary_decision": "promotion_candidate_ready",
        }

    return {
        "schema_version": "modern_docx_omml_promotion_preflight.v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "mode": "promotion_preflight",
            "modern_docx_only": True,
            "patch_behavior_changed": False,
            "inventory": _to_rel(inventory_path),
        },
        "criteria": {
            "structural_suitable": "parseable document.xml + native OMML present + embedded object tags present",
            "ci_safe": "preflight practical threshold: size<=1MB and total OMML<=50 and object_like_tags<=600",
            "repo_trackable": "candidate is already repo-tracked",
            "confidence_gain_if_promoted": "high for mixed inline+block object+OMML, medium for object+OMML non-mixed, low otherwise",
        },
        "candidate_evaluations": evaluations,
        "overall": overall,
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run promotion preflight for local-only modern DOCX + OMML candidates.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.inventory.resolve())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Promotion preflight report: {output}")
    print(
        "Summary: "
        f"candidates={len(report['candidate_evaluations'])} "
        f"decision={report['overall']['summary_decision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
