#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.generate_modern_docx_omml_output_manifest import (
    DEFAULT_OUTPUT_ROOT,
    main as generate_manifest_main,
)
from scripts.workflow.validate_modern_docx_omml import validate_inventory
from scripts.workflow.validate_modern_docx_omml_structure import _augment_report
from scripts.workflow.validate_modern_docx_omml_structure import main as validate_structure_main


GENERATED_MANIFEST = DEFAULT_OUTPUT_ROOT / "modern_docx_omml_generated_outputs.json"
GENERATED_GATE_REPORT = DEFAULT_OUTPUT_ROOT / "modern_docx_omml_generated_output_gate_report.json"
REQUIRED_DOCX_PARTS = ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]


def _summary_line(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Summary: "):
            return line
    return "Summary: unavailable"


def _resolve_generated_docx(manifest_path: Path, case: Dict[str, Any]) -> Path:
    raw_path = str(case.get("generated_docx") or case.get("output_docx") or "").strip()
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def check_docx_openability(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "path": str(path),
        "zip_package": False,
        "content_types": False,
        "root_relationships": False,
        "document_xml": False,
        "document_xml_parseable": False,
        "passed": False,
        "failures": [],
    }
    if not path.exists():
        result["failures"].append("file not found")
        return result

    try:
        with zipfile.ZipFile(path) as docx:
            result["zip_package"] = True
            names = set(docx.namelist())
            for part in REQUIRED_DOCX_PARTS:
                if part not in names:
                    result["failures"].append(f"{part} missing")
            result["content_types"] = "[Content_Types].xml" in names
            result["root_relationships"] = "_rels/.rels" in names
            result["document_xml"] = "word/document.xml" in names
            if result["document_xml"]:
                try:
                    ElementTree.fromstring(docx.read("word/document.xml"))
                    result["document_xml_parseable"] = True
                except ElementTree.ParseError as exc:
                    result["failures"].append(f"word/document.xml not parseable: {exc}")
    except zipfile.BadZipFile:
        result["failures"].append("not a readable DOCX zip package")
    except OSError as exc:
        result["failures"].append(f"could not read DOCX: {exc}")

    result["passed"] = (
        result["zip_package"]
        and result["content_types"]
        and result["root_relationships"]
        and result["document_xml"]
        and result["document_xml_parseable"]
    )
    return result


def validate_generated_openability(manifest_path: Path) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("generated-output manifest cases must be a list")

    results: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        docx_path = _resolve_generated_docx(manifest_path, case)
        result = check_docx_openability(docx_path)
        result["case_id"] = str(case.get("case_id", "")).strip()
        results.append(result)

    failed = [result for result in results if not result["passed"]]
    return {
        "case_count": len(results),
        "passed_count": len(results) - len(failed),
        "failed_count": len(failed),
        "results": results,
    }


def render_openability_summary(report: Dict[str, Any]) -> str:
    return (
        "Openability: "
        f"cases={report['case_count']} "
        f"passed={report['passed_count']} "
        f"failed={report['failed_count']}"
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_structural_report(manifest_path: Path) -> Dict[str, Any]:
    return _augment_report(validate_inventory(manifest_path.resolve()))


def _structural_summary(report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(report, dict):
        return {"status": "not_run"}
    return {
        "status": "passed" if report.get("unexpected_failed_count", 0) == 0 and report.get("structural_failed_check_count", 0) == 0 else "failed",
        "case_count": report.get("case_count", 0),
        "passed_count": report.get("passed_count", 0),
        "expected_failed_count": report.get("expected_failed_count", 0),
        "unexpected_failed_count": report.get("unexpected_failed_count", 0),
        "skipped_count": report.get("skipped_count", 0),
        "structural_failed_check_count": report.get("structural_failed_check_count", 0),
    }


def _case_statuses(
    openability_report: Optional[Dict[str, Any]],
    structural_report: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    combined: Dict[str, Dict[str, Any]] = {}
    for result in openability_report.get("results", []) if isinstance(openability_report, dict) else []:
        if not isinstance(result, dict):
            continue
        case_id = str(result.get("case_id", "")).strip()
        if not case_id:
            continue
        combined[case_id] = {
            "case_id": case_id,
            "openability_status": "passed" if result.get("passed") else "failed",
            "structural_status": "not_run",
            "gate_status": "passed" if result.get("passed") else "failed",
        }
    for case in structural_report.get("cases", []) if isinstance(structural_report, dict) else []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if not case_id:
            continue
        entry = combined.setdefault(
            case_id,
            {
                "case_id": case_id,
                "openability_status": "not_run",
                "structural_status": "not_run",
                "gate_status": "not_run",
            },
        )
        entry["structural_status"] = str(case.get("result", "unknown"))
        if entry["openability_status"] == "failed" or entry["structural_status"] not in {"passed", "expected_failed", "skipped"}:
            entry["gate_status"] = "failed"
        elif entry["openability_status"] == "passed":
            entry["gate_status"] = "passed"
    return [combined[key] for key in sorted(combined)]


def _write_gate_report(
    manifest_path: Path,
    generation_result: str,
    openability_report: Optional[Dict[str, Any]],
    structural_report: Optional[Dict[str, Any]],
    overall_gate_result: str,
) -> None:
    payload = {
        "timestamp": _utc_timestamp(),
        "manifest_path": str(manifest_path),
        "generation_result": generation_result,
        "openability_summary": {
            "status": (
                "not_run"
                if not isinstance(openability_report, dict)
                else "passed" if openability_report.get("failed_count", 0) == 0 else "failed"
            ),
            "case_count": openability_report.get("case_count", 0) if isinstance(openability_report, dict) else 0,
            "passed_count": openability_report.get("passed_count", 0) if isinstance(openability_report, dict) else 0,
            "failed_count": openability_report.get("failed_count", 0) if isinstance(openability_report, dict) else 0,
        },
        "structural_summary": _structural_summary(structural_report),
        "case_statuses": _case_statuses(openability_report, structural_report),
        "overall_gate_result": overall_gate_result,
    }
    GENERATED_GATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_GATE_REPORT.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv:
        raise SystemExit("This gate does not accept arguments.")

    print("Modern DOCX + OMML generated-output gate")
    print(f"Manifest: {GENERATED_MANIFEST}")

    generation_output = StringIO()
    with contextlib.redirect_stdout(generation_output):
        generation_rc = generate_manifest_main([])
    if generation_rc != 0:
        print("Generation: failed")
        _write_gate_report(
            GENERATED_MANIFEST,
            generation_result="failed",
            openability_report=None,
            structural_report=None,
            overall_gate_result="failed",
        )
        return generation_rc
    print("Generation: passed")

    try:
        openability_report = validate_generated_openability(GENERATED_MANIFEST)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Openability: failed ({exc})")
        _write_gate_report(
            GENERATED_MANIFEST,
            generation_result="passed",
            openability_report=None,
            structural_report=None,
            overall_gate_result="failed",
        )
        return 1
    print(render_openability_summary(openability_report))
    if openability_report["failed_count"]:
        print("Openability validation: failed")
        _write_gate_report(
            GENERATED_MANIFEST,
            generation_result="passed",
            openability_report=openability_report,
            structural_report=None,
            overall_gate_result="failed",
        )
        return 1
    print("Openability validation: passed")

    validation_output = StringIO()
    with contextlib.redirect_stdout(validation_output):
        validation_rc = validate_structure_main(["--inventory", str(GENERATED_MANIFEST)])
    structural_report = _build_structural_report(GENERATED_MANIFEST)
    print(_summary_line(validation_output.getvalue()))
    print("Structural validation: " + ("passed" if validation_rc == 0 else "failed"))
    _write_gate_report(
        GENERATED_MANIFEST,
        generation_result="passed",
        openability_report=openability_report,
        structural_report=structural_report,
        overall_gate_result="passed" if validation_rc == 0 else "failed",
    )
    return validation_rc


if __name__ == "__main__":
    raise SystemExit(main())
