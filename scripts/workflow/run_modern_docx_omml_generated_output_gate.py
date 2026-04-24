#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.generate_modern_docx_omml_output_manifest import (
    DEFAULT_OUTPUT_ROOT,
    main as generate_manifest_main,
)
from scripts.workflow.validate_modern_docx_omml import inspect_docx, validate_inventory
from scripts.workflow.validate_modern_docx_omml_structure import _augment_report
from scripts.workflow.validate_modern_docx_omml_structure import main as validate_structure_main


GENERATED_MANIFEST = DEFAULT_OUTPUT_ROOT / "modern_docx_omml_generated_outputs.json"
GENERATED_GATE_REPORT = DEFAULT_OUTPUT_ROOT / "modern_docx_omml_generated_output_gate_report.json"
REQUIRED_DOCX_PARTS = ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
PACKAGE_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CORE_PROPS_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
CORE_PROPS_PART_NAME = "/docProps/core.xml"
CORE_PROPS_TARGET = "docProps/core.xml"
CORE_PROPS_CONTENT_TYPE = "application/vnd.openxmlformats-package.core-properties+xml"
CORE_PROPS_REL_TYPE = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
SERIALIZER_NORMALIZATION_ALLOWED_DIFFS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
}
SERIALIZER_ONLY_DRIFT = "serializer_only_drift"
STRUCTURAL_DRIFT = "structural_drift"
NO_DRIFT = "no_drift"


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


def _resolve_source_docx(case: Dict[str, Any]) -> Path:
    raw_path = str(case.get("source_docx") or "").strip()
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return ROOT / path


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


def _inspection_snapshot(inspection: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "document_xml_exists": bool(inspection.get("document_xml_exists")),
        "document_xml_parseable": bool(inspection.get("document_xml_parseable")),
        "equation_count": int(inspection.get("omath_count", 0) or 0),
        "block_equation_count": int(inspection.get("omathpara_count", 0) or 0),
        "inline_equation_count": int(inspection.get("inline_omath_count", 0) or 0),
        "placement_summary": str(inspection.get("placement_summary", "")),
        "paragraph_run_safety_summary": str(inspection.get("paragraph_run_safety_summary", "")),
        "inline_paragraph_run_context_safe": bool(inspection.get("inline_paragraph_run_context_safe")),
        "block_omathpara_context_safe": bool(inspection.get("block_omathpara_context_safe")),
        "surrounding_non_math_text_preserved": bool(inspection.get("surrounding_non_math_text_preserved")),
    }


def _drift_origin_hint(source: Dict[str, Any], output: Dict[str, Any]) -> str:
    if not source.get("document_xml_parseable") or not output.get("document_xml_parseable"):
        return "document_xml_unavailable_for_comparison"
    if (
        source.get("equation_count") != output.get("equation_count")
        or source.get("block_equation_count") != output.get("block_equation_count")
        or source.get("inline_equation_count") != output.get("inline_equation_count")
    ):
        return "equation_count_or_block_inline_split_changed_across_patch_docx"
    if source.get("placement_summary") != output.get("placement_summary"):
        return "placement_summary_changed_across_patch_docx"
    if (
        source.get("paragraph_run_safety_summary") != output.get("paragraph_run_safety_summary")
        or source.get("inline_paragraph_run_context_safe") != output.get("inline_paragraph_run_context_safe")
        or source.get("block_omathpara_context_safe") != output.get("block_omathpara_context_safe")
        or source.get("surrounding_non_math_text_preserved") != output.get("surrounding_non_math_text_preserved")
    ):
        return "paragraph_run_context_changed_across_patch_docx"
    return "no_structural_drift_detected"


def _read_docx_package(path: Path) -> Dict[str, bytes]:
    with zipfile.ZipFile(path) as docx:
        return {name: docx.read(name) for name in docx.namelist()}


def _xml_root(xml_bytes: bytes) -> ElementTree.Element:
    return ElementTree.fromstring(xml_bytes)


def _xml_signature(element: ElementTree.Element) -> Tuple[Any, ...]:
    return (
        element.tag,
        tuple(sorted(element.attrib.items())),
        (element.text or "").strip(),
        tuple(_xml_signature(child) for child in list(element)),
    )


def _canonical_xml_signature(xml_bytes: bytes) -> Optional[Tuple[Any, ...]]:
    try:
        root = _xml_root(xml_bytes)
    except ElementTree.ParseError:
        return None
    return _xml_signature(root)


def _canonical_content_types(xml_bytes: bytes) -> Optional[Tuple[Any, ...]]:
    try:
        root = _xml_root(xml_bytes)
    except ElementTree.ParseError:
        return None
    for child in list(root):
        if (
            child.tag == f"{{{CONTENT_TYPES_NS}}}Override"
            and child.attrib.get("PartName") == CORE_PROPS_PART_NAME
            and child.attrib.get("ContentType") == CORE_PROPS_CONTENT_TYPE
        ):
            root.remove(child)
    return _xml_signature(root)


def _canonical_root_relationships(xml_bytes: bytes) -> Optional[Tuple[Any, ...]]:
    try:
        root = _xml_root(xml_bytes)
    except ElementTree.ParseError:
        return None
    for child in list(root):
        if (
            child.tag == f"{{{PACKAGE_RELS_NS}}}Relationship"
            and child.attrib.get("Target") == CORE_PROPS_TARGET
            and child.attrib.get("Type") == CORE_PROPS_REL_TYPE
        ):
            root.remove(child)
    return _xml_signature(root)


def _is_empty_core_properties(xml_bytes: bytes) -> bool:
    try:
        root = _xml_root(xml_bytes)
    except ElementTree.ParseError:
        return False
    return (
        root.tag == f"{{{CORE_PROPS_NS}}}coreProperties"
        and len(list(root)) == 0
        and not (root.text or "").strip()
    )


def _package_drift_details(source_docx: Path, output_docx: Path) -> Dict[str, Any]:
    try:
        source_package = _read_docx_package(source_docx)
        output_package = _read_docx_package(output_docx)
    except (OSError, zipfile.BadZipFile):
        return {
            "package_diff_observed": False,
            "serializer_only_safe": False,
            "reason": "package_unavailable_for_comparison",
        }

    source_names = set(source_package)
    output_names = set(output_package)
    extra_output_parts = sorted(output_names - source_names)
    missing_output_parts = sorted(source_names - output_names)
    differing_parts = sorted(
        name for name in (source_names & output_names) if source_package[name] != output_package[name]
    )

    details: Dict[str, Any] = {
        "package_diff_observed": bool(extra_output_parts or missing_output_parts or differing_parts),
        "extra_output_parts": extra_output_parts,
        "missing_output_parts": missing_output_parts,
        "differing_parts": differing_parts,
        "serializer_only_safe": False,
        "reason": "package_bytes_identical",
    }
    if not details["package_diff_observed"]:
        return details

    if missing_output_parts:
        details["reason"] = "output_missing_existing_package_parts"
        return details
    if any(part != "docProps/core.xml" for part in extra_output_parts):
        details["reason"] = "unexpected_added_package_parts"
        return details
    if any(part not in SERIALIZER_NORMALIZATION_ALLOWED_DIFFS for part in differing_parts):
        details["reason"] = "unexpected_package_parts_changed"
        return details

    if "docProps/core.xml" in output_package and not _is_empty_core_properties(output_package["docProps/core.xml"]):
        details["reason"] = "added_core_properties_part_is_not_empty_normalization"
        return details

    document_xml_same = _canonical_xml_signature(source_package["word/document.xml"]) == _canonical_xml_signature(
        output_package["word/document.xml"]
    )
    content_types_same = _canonical_content_types(source_package["[Content_Types].xml"]) == _canonical_content_types(
        output_package["[Content_Types].xml"]
    )
    root_relationships_same = _canonical_root_relationships(source_package["_rels/.rels"]) == _canonical_root_relationships(
        output_package["_rels/.rels"]
    )
    if document_xml_same and content_types_same and root_relationships_same:
        details["serializer_only_safe"] = True
        details["reason"] = "package_xml_normalization_only"
        return details

    details["reason"] = "package_xml_difference_not_limited_to_known_normalization"
    return details


def _classify_drift(
    source_snapshot: Dict[str, Any],
    output_snapshot: Dict[str, Any],
    source_docx: Path,
    output_docx: Path,
    drift_origin_hint: str,
) -> Tuple[str, str, Dict[str, Any]]:
    if drift_origin_hint != "no_structural_drift_detected":
        return STRUCTURAL_DRIFT, drift_origin_hint, {"reason": drift_origin_hint}

    package_details = _package_drift_details(source_docx, output_docx)
    if not package_details.get("package_diff_observed"):
        return NO_DRIFT, "package_bytes_identical", package_details
    if package_details.get("serializer_only_safe"):
        return SERIALIZER_ONLY_DRIFT, str(package_details.get("reason", "")), package_details
    return STRUCTURAL_DRIFT, str(package_details.get("reason", "")), package_details


def _build_patch_path_diagnostics(manifest_path: Path) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("generated-output manifest cases must be a list")

    diagnostics: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        source_inspection = inspect_docx(_resolve_source_docx(case))
        source_docx = _resolve_source_docx(case)
        output_docx = _resolve_generated_docx(manifest_path, case)
        output_inspection = inspect_docx(output_docx)
        source_snapshot = _inspection_snapshot(source_inspection)
        output_snapshot = _inspection_snapshot(output_inspection)
        drift_origin_hint = _drift_origin_hint(source_snapshot, output_snapshot)
        drift_class, drift_class_reason, package_details = _classify_drift(
            source_snapshot,
            output_snapshot,
            source_docx,
            output_docx,
            drift_origin_hint,
        )
        diagnostics.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "source_docx": str(case.get("source_docx", "")).strip(),
                "generated_docx": str(case.get("generated_docx", "")).strip(),
                "source": source_snapshot,
                "output": output_snapshot,
                "drift_origin_hint": drift_origin_hint,
                "drift_class": drift_class,
                "drift_class_reason": drift_class_reason,
                "package_diff_details": package_details,
                "patch_summary_record": case.get("patch_summary_record")
                if isinstance(case.get("patch_summary_record"), dict)
                else None,
            }
        )

    drift_candidates = [
        item for item in diagnostics if item.get("drift_origin_hint") != "no_structural_drift_detected"
    ]
    drift_class_counts = {
        NO_DRIFT: sum(1 for item in diagnostics if item.get("drift_class") == NO_DRIFT),
        SERIALIZER_ONLY_DRIFT: sum(1 for item in diagnostics if item.get("drift_class") == SERIALIZER_ONLY_DRIFT),
        STRUCTURAL_DRIFT: sum(1 for item in diagnostics if item.get("drift_class") == STRUCTURAL_DRIFT),
    }
    return {
        "case_count": len(diagnostics),
        "drift_candidate_count": len(drift_candidates),
        "drift_class_counts": drift_class_counts,
        "cases": diagnostics,
    }


def render_patch_path_diagnostics_summary(report: Optional[Dict[str, Any]]) -> str:
    if not isinstance(report, dict):
        return "Patch-path diagnostics: not_run"
    counts = report.get("drift_class_counts", {})
    attention_case_ids: List[str] = []
    attention_expected = 0
    attention_unexpected = 0
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        patch_summary = case.get("patch_summary_record", {}) if isinstance(case.get("patch_summary_record"), dict) else {}
        omml_preservation = str(patch_summary.get("omml_preservation", "")).strip()
        omml_drift_class = str(patch_summary.get("omml_drift_class", "")).strip()
        omml_drift_warning = str(patch_summary.get("omml_drift_warning", "")).strip()
        if omml_preservation.startswith("drift_") or omml_drift_class or omml_drift_warning:
            attention_case_ids.append(str(case.get("case_id", "")).strip())
            if omml_drift_class == "expected_patch_drift":
                attention_expected += 1
            elif omml_drift_class == "unexpected_native_drift":
                attention_unexpected += 1
    attention_case_ids = [case_id for case_id in attention_case_ids if case_id]
    attention_case_ids.sort()
    lines = [
        "Patch-path diagnostics: "
        f"cases={report.get('case_count', 0)} "
        f"drift_candidates={report.get('drift_candidate_count', 0)} "
        f"serializer_only={counts.get(SERIALIZER_ONLY_DRIFT, 0)} "
        f"attention_cases={len(attention_case_ids)} "
        f"attention_expected={attention_expected} "
        f"attention_unexpected={attention_unexpected}"
    ]
    if attention_case_ids:
        lines.append(f"Patch-path attention case_ids: {','.join(attention_case_ids)}")
    attention_cases: List[str] = []
    for case in report.get("cases", []):
        if not isinstance(case, dict):
            continue
        hint = str(case.get("drift_origin_hint", ""))
        drift_class = str(case.get("drift_class", ""))
        patch_summary = case.get("patch_summary_record", {}) if isinstance(case.get("patch_summary_record"), dict) else {}
        omml_preservation = str(patch_summary.get("omml_preservation", "")).strip()
        omml_drift_class = str(patch_summary.get("omml_drift_class", "")).strip()
        omml_drift_warning = str(patch_summary.get("omml_drift_warning", "")).strip()
        if drift_class == SERIALIZER_ONLY_DRIFT:
            lines.append(
                f"- {case.get('case_id', '')}: {SERIALIZER_ONLY_DRIFT}"
            )
        elif hint != "no_structural_drift_detected":
            lines.append(f"- {case.get('case_id', '')}: {hint}")
        if omml_preservation.startswith("drift_") or omml_drift_class or omml_drift_warning:
            attention_cases.append(
                f"- {case.get('case_id', '')}: "
                f"omml_attention preservation={omml_preservation or 'n/a'} "
                f"drift_class={omml_drift_class or 'n/a'} "
                f"drift_warning={omml_drift_warning or 'n/a'}"
            )
    if attention_cases:
        attention_cases.sort()
        lines.append("Patch-path OMML attention:")
        lines.extend(attention_cases)
    return "\n".join(lines)


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


def _structural_diffs(structural_report: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(structural_report, dict):
        return []
    diffs: List[Dict[str, Any]] = []
    for case in structural_report.get("cases", []):
        if not isinstance(case, dict):
            continue
        checks = [
            {
                "name": str(check.get("name", "")),
                "expected": check.get("expected"),
                "actual": check.get("actual"),
                "passed": bool(check.get("passed")),
            }
            for check in case.get("structural_checks", [])
            if isinstance(check, dict) and check.get("expected") is not None
        ]
        diffs.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "status": str(case.get("result", "")),
                "structural_checks": checks,
            }
        )
    return diffs


def _failed_structural_diffs(structural_report: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failed: List[Dict[str, Any]] = []
    for case in _structural_diffs(structural_report):
        failed_checks = [
            check
            for check in case.get("structural_checks", [])
            if isinstance(check, dict) and not bool(check.get("passed"))
        ]
        if failed_checks:
            failed.append(
                {
                    "case_id": case.get("case_id", ""),
                    "structural_checks": failed_checks,
                }
            )
    return failed


def render_structural_drift_summary(structural_report: Optional[Dict[str, Any]]) -> str:
    failed_cases = _failed_structural_diffs(structural_report)
    if not failed_cases:
        return "Structural drift summary: no failed structural diffs"

    lines = ["Structural drift summary:"]
    for case in failed_cases:
        lines.append(f"- {case.get('case_id', '')}")
        for check in case.get("structural_checks", []):
            lines.append(
                f"  {check.get('name', '')}: "
                f"expected={check.get('expected')!r} actual={check.get('actual')!r}"
            )
    return "\n".join(lines)


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
    patch_path_diagnostics: Optional[Dict[str, Any]],
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
        "structural_diffs": _structural_diffs(structural_report),
        "patch_path_diagnostics": patch_path_diagnostics if isinstance(patch_path_diagnostics, dict) else {"status": "not_run"},
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
            patch_path_diagnostics=None,
            overall_gate_result="failed",
        )
        return generation_rc
    print("Generation: passed")

    try:
        patch_path_diagnostics = _build_patch_path_diagnostics(GENERATED_MANIFEST)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Patch-path diagnostics: failed ({exc})")
        _write_gate_report(
            GENERATED_MANIFEST,
            generation_result="passed",
            openability_report=None,
            structural_report=None,
            patch_path_diagnostics=None,
            overall_gate_result="failed",
        )
        return 1

    try:
        openability_report = validate_generated_openability(GENERATED_MANIFEST)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Openability: failed ({exc})")
        _write_gate_report(
            GENERATED_MANIFEST,
            generation_result="passed",
            openability_report=None,
            structural_report=None,
            patch_path_diagnostics=patch_path_diagnostics,
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
            patch_path_diagnostics=patch_path_diagnostics,
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
    print(render_structural_drift_summary(structural_report))
    print(render_patch_path_diagnostics_summary(patch_path_diagnostics))
    _write_gate_report(
        GENERATED_MANIFEST,
        generation_result="passed",
        openability_report=openability_report,
        structural_report=structural_report,
        patch_path_diagnostics=patch_path_diagnostics,
        overall_gate_result="passed" if validation_rc == 0 else "failed",
    )
    return validation_rc


if __name__ == "__main__":
    raise SystemExit(main())
