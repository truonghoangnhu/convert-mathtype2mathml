#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "regression_set" / "modern_docx_omml_inventory.json"
DOCUMENT_XML = "word/document.xml"
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SCHEMA_VERSION = "modern_docx_omml_validation.v1"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag


def _namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def _is_omml(element: ElementTree.Element, local_name: str) -> bool:
    return _namespace(element.tag) == OMML_NS and _local_name(element.tag) == local_name


def _is_word(element: ElementTree.Element, local_name: str) -> bool:
    return _namespace(element.tag) == WORD_NS and _local_name(element.tag) == local_name


def _count_inline_omath(root: ElementTree.Element) -> int:
    # V1 heuristic: oMath inside oMathPara is block-owned; oMath elsewhere is inline.
    def visit(element: ElementTree.Element, in_omath_para: bool) -> int:
        current_in_para = in_omath_para or _is_omml(element, "oMathPara")
        count = 0
        if _is_omml(element, "oMath") and not current_in_para:
            count += 1
        for child in list(element):
            count += visit(child, current_in_para)
        return count

    return visit(root, False)


def _compute_placement_summary(inline_omath_count: int, omathpara_count: int) -> str:
    if inline_omath_count > 0 and omathpara_count > 0:
        return f"mixed inline/block OMML: inline_oMath={inline_omath_count} oMathPara={omathpara_count}"
    if inline_omath_count > 0:
        return f"inline OMML only: inline_oMath={inline_omath_count}"
    if omathpara_count > 0:
        return f"block OMML only: oMathPara={omathpara_count}"
    return "no OMML math"


def _basic_omml_structure_valid(root: ElementTree.Element) -> bool:
    omath_count = 0
    for element in root.iter():
        if _is_omml(element, "oMath"):
            omath_count += 1
        if _is_omml(element, "oMathPara") and not any(_is_omml(child, "oMath") for child in list(element)):
            return False
    return omath_count > 0


def _paragraph_tokens(element: ElementTree.Element) -> List[Tuple[str, str]]:
    if _is_omml(element, "oMathPara"):
        return [("block_math", "")]
    if _is_omml(element, "oMath"):
        return [("inline_math", "")]
    if _is_word(element, "t"):
        return [("text", element.text or "")]

    tokens: List[Tuple[str, str]] = []
    for child in list(element):
        tokens.extend(_paragraph_tokens(child))
    return tokens


def _paragraph_run_safety(root: ElementTree.Element) -> Dict[str, Any]:
    total_inline_math_count = 0
    total_block_math_count = 0
    inline_math_paragraph_count = 0
    inline_math_text_paragraph_count = 0
    inline_math_text_before_after_count = 0
    block_math_paragraph_count = 0
    multi_inline_paragraph_count = 0

    for paragraph in (element for element in root.iter() if _is_word(element, "p")):
        tokens = _paragraph_tokens(paragraph)
        inline_positions = [index for index, (kind, _) in enumerate(tokens) if kind == "inline_math"]
        block_count = sum(1 for kind, _ in tokens if kind == "block_math")
        non_math_text_positions = [
            index for index, (kind, value) in enumerate(tokens) if kind == "text" and value.strip()
        ]
        total_inline_math_count += len(inline_positions)
        total_block_math_count += block_count

        if inline_positions:
            inline_math_paragraph_count += 1
            if len(inline_positions) >= 2:
                multi_inline_paragraph_count += 1
            if non_math_text_positions:
                inline_math_text_paragraph_count += 1
            if non_math_text_positions and any(index < inline_positions[0] for index in non_math_text_positions) and any(
                index > inline_positions[-1] for index in non_math_text_positions
            ):
                inline_math_text_before_after_count += 1
        if block_count:
            block_math_paragraph_count += 1

    inline_context_safe = total_inline_math_count == 0 or inline_math_paragraph_count >= 1
    block_context_safe = total_block_math_count == 0 or block_math_paragraph_count >= 1
    surrounding_non_math_text_preserved = (
        inline_math_paragraph_count == 0 or inline_math_text_before_after_count == inline_math_paragraph_count
    )
    summary = (
        f"inline_paragraphs={inline_math_paragraph_count} "
        f"inline_with_text={inline_math_text_paragraph_count} "
        f"inline_with_text_before_after={inline_math_text_before_after_count} "
        f"block_paragraphs={block_math_paragraph_count} "
        f"multi_inline_paragraphs={multi_inline_paragraph_count}"
    )
    return {
        "inline_math_paragraph_count": inline_math_paragraph_count,
        "inline_math_text_paragraph_count": inline_math_text_paragraph_count,
        "inline_math_text_before_after_count": inline_math_text_before_after_count,
        "block_math_paragraph_count": block_math_paragraph_count,
        "multi_inline_paragraph_count": multi_inline_paragraph_count,
        "inline_paragraph_run_context_safe": inline_context_safe,
        "block_omathpara_context_safe": block_context_safe,
        "surrounding_non_math_text_preserved": surrounding_non_math_text_preserved,
        "paragraph_run_safety_summary": summary,
    }


def inspect_docx(path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "file_path": str(path),
        "exists": path.exists(),
        "document_xml_exists": False,
        "document_xml_parseable": False,
        "omath_count": 0,
        "omathpara_count": 0,
        "inline_omath_count": 0,
        "appears_inline_math": False,
        "appears_block_math": False,
        "basic_omml_structure_present": False,
        "basic_omml_structure_valid": False,
        "placement_summary": "unavailable",
        "inline_paragraph_run_context_safe": False,
        "block_omathpara_context_safe": False,
        "surrounding_non_math_text_preserved": False,
        "paragraph_run_safety_summary": "unavailable",
        "errors": [],
    }

    if not path.exists():
        result["errors"].append("file not found")
        return result

    try:
        with zipfile.ZipFile(path) as docx:
            if DOCUMENT_XML not in docx.namelist():
                result["errors"].append(f"{DOCUMENT_XML} not found")
                return result
            result["document_xml_exists"] = True
            document_xml = docx.read(DOCUMENT_XML)
    except zipfile.BadZipFile:
        result["errors"].append("not a readable DOCX zip package")
        return result
    except OSError as exc:
        result["errors"].append(f"could not read DOCX: {exc}")
        return result

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        result["errors"].append(f"{DOCUMENT_XML} is not parseable XML: {exc}")
        return result

    result["document_xml_parseable"] = True
    omath_count = sum(1 for element in root.iter() if _is_omml(element, "oMath"))
    omathpara_count = sum(1 for element in root.iter() if _is_omml(element, "oMathPara"))
    inline_omath_count = _count_inline_omath(root)

    result["omath_count"] = omath_count
    result["omathpara_count"] = omathpara_count
    result["inline_omath_count"] = inline_omath_count
    result["appears_inline_math"] = inline_omath_count > 0
    result["appears_block_math"] = omathpara_count > 0
    result["basic_omml_structure_present"] = omath_count > 0 or omathpara_count > 0
    result["basic_omml_structure_valid"] = _basic_omml_structure_valid(root)
    result["placement_summary"] = _compute_placement_summary(inline_omath_count, omathpara_count)
    result.update(_paragraph_run_safety(root))
    return result


def _resolve_source_docx(source_docx: str, inventory_path: Path) -> Optional[Path]:
    value = source_docx.strip()
    if not value or value == "TODO":
        return None
    path = Path(value)
    if path.is_absolute():
        return path

    inventory_relative = (inventory_path.parent / path).resolve()
    if inventory_relative.exists():
        return inventory_relative
    return (ROOT / path).resolve()


def _expected_int(expected: Dict[str, Any], key: str) -> Optional[int]:
    value = expected.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _expected_bool(expected: Dict[str, Any], key: str) -> Optional[bool]:
    value = expected.get(key)
    if isinstance(value, bool):
        return value
    return None


def _expected_string(expected: Dict[str, Any], key: str) -> Optional[str]:
    value = expected.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _structural_check(name: str, actual: Any, expected: Any) -> Dict[str, Any]:
    return {
        "name": name,
        "actual": actual,
        "expected": expected,
        "passed": expected is None or actual == expected,
    }


def build_structural_checks(case: Dict[str, Any], inspection: Dict[str, Any]) -> List[Dict[str, Any]]:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        expected = {}

    return [
        _structural_check(
            "document_xml_exists",
            bool(inspection.get("document_xml_exists")),
            _expected_bool(expected, "document_xml_exists"),
        ),
        _structural_check(
            "document_xml_parseable",
            bool(inspection.get("document_xml_parseable")),
            _expected_bool(expected, "document_xml_parseable"),
        ),
        _structural_check(
            "equation_count",
            int(inspection.get("omath_count", 0) or 0),
            _expected_int(expected, "equation_count"),
        ),
        _structural_check(
            "block_equation_count",
            int(inspection.get("omathpara_count", 0) or 0),
            _expected_int(expected, "block_equation_count"),
        ),
        _structural_check(
            "inline_equation_count",
            int(inspection.get("inline_omath_count", 0) or 0),
            _expected_int(expected, "inline_equation_count"),
        ),
        _structural_check(
            "appears_inline_math",
            bool(inspection.get("appears_inline_math")),
            _expected_bool(expected, "appears_inline_math"),
        ),
        _structural_check(
            "appears_block_math",
            bool(inspection.get("appears_block_math")),
            _expected_bool(expected, "appears_block_math"),
        ),
        _structural_check(
            "basic_omml_structure_present",
            bool(inspection.get("basic_omml_structure_present")),
            _expected_bool(expected, "basic_omml_structure_present"),
        ),
        _structural_check(
            "placement_summary",
            str(inspection.get("placement_summary", "")),
            _expected_string(expected, "computed_placement_summary"),
        ),
        _structural_check(
            "basic_omml_structure_valid",
            bool(inspection.get("basic_omml_structure_valid")),
            _expected_bool(expected, "valid_omath_omathpara_structure"),
        ),
        _structural_check(
            "inline_paragraph_run_context_safe",
            bool(inspection.get("inline_paragraph_run_context_safe")),
            _expected_bool(expected, "inline_paragraph_run_context_safe"),
        ),
        _structural_check(
            "block_omathpara_context_safe",
            bool(inspection.get("block_omathpara_context_safe")),
            _expected_bool(expected, "block_omathpara_context_safe"),
        ),
        _structural_check(
            "surrounding_non_math_text_preserved",
            bool(inspection.get("surrounding_non_math_text_preserved")),
            _expected_bool(expected, "surrounding_non_math_text_preserved"),
        ),
        _structural_check(
            "paragraph_run_safety_summary",
            str(inspection.get("paragraph_run_safety_summary", "")),
            _expected_string(expected, "paragraph_run_safety_summary"),
        ),
    ]


def _expected_status(case: Dict[str, Any]) -> str:
    value = str(case.get("expected_status", "")).strip()
    if value in {"passed", "failed"}:
        return value
    expected = case.get("expected", {})
    if isinstance(expected, dict):
        value = str(expected.get("expected_status", "")).strip()
        if value in {"passed", "failed"}:
            return value
    return "passed"


def _validate_flags(case: Dict[str, Any], inspection: Dict[str, Any]) -> List[str]:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        return []

    failures: List[str] = []
    for key in [
        "document_xml_exists",
        "document_xml_parseable",
        "appears_inline_math",
        "appears_block_math",
        "basic_omml_structure_present",
        "inline_paragraph_run_context_safe",
        "block_omathpara_context_safe",
        "surrounding_non_math_text_preserved",
    ]:
        expected_value = _expected_bool(expected, key)
        if expected_value is None:
            continue
        actual_value = bool(inspection.get(key))
        if actual_value != expected_value:
            failures.append(f"{key} expected {expected_value}, found {actual_value}")
    return failures


def _validate_counts(case: Dict[str, Any], inspection: Dict[str, Any]) -> List[str]:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        return []

    checks: List[Tuple[str, str]] = [
        ("equation_count", "omath_count"),
        ("block_equation_count", "omathpara_count"),
    ]
    failures: List[str] = []
    for expected_key, actual_key in checks:
        expected_value = _expected_int(expected, expected_key)
        if expected_value is None:
            continue
        actual_value = int(inspection.get(actual_key, 0) or 0)
        if actual_value != expected_value:
            failures.append(f"{expected_key} expected {expected_value}, found {actual_value}")

    inline_expected = _expected_int(expected, "inline_equation_count")
    if inline_expected is not None:
        inline_found = int(inspection.get("inline_omath_count", 0) or 0)
        if inline_found != inline_expected:
            failures.append(f"inline_equation_count expected {inline_expected}, found {inline_found}")
    return failures


def _validate_summaries(case: Dict[str, Any], inspection: Dict[str, Any]) -> List[str]:
    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        return []

    failures: List[str] = []
    summary_checks: List[Tuple[str, str]] = [
        ("computed_placement_summary", "placement_summary"),
        ("paragraph_run_safety_summary", "paragraph_run_safety_summary"),
    ]
    for expected_key, actual_key in summary_checks:
        expected_value = _expected_string(expected, expected_key)
        if expected_value is None:
            continue
        actual_value = str(inspection.get(actual_key, ""))
        if actual_value != expected_value:
            label = "placement_summary" if actual_key == "placement_summary" else actual_key
            failures.append(f"{label} expected {expected_value!r}, found {actual_value!r}")
    return failures


def validate_case(case: Dict[str, Any], inventory_path: Path) -> Dict[str, Any]:
    case_id = str(case.get("case_id", "")).strip()
    source_docx_value = str(case.get("source_docx", "")).strip()
    target_docx_value = str(case.get("output_docx") or case.get("generated_docx") or source_docx_value).strip()
    classification = str(case.get("classification", "")).strip() or "unknown"
    target_docx = _resolve_source_docx(target_docx_value, inventory_path)

    result: Dict[str, Any] = {
        "case_id": case_id,
        "source_docx": source_docx_value,
        "target_docx": target_docx_value,
        "classification": classification,
        "expected_status": _expected_status(case),
        "status": "failed",
        "result": "unexpected_failed",
        "failures": [],
        "inspection": None,
        "structural_checks": [],
    }

    if target_docx is None:
        result["status"] = "skipped"
        result["result"] = "skipped"
        result["failures"] = ["target DOCX is not set"]
        return result

    inspection = inspect_docx(target_docx)
    result["inspection"] = inspection
    result["structural_checks"] = build_structural_checks(case, inspection)

    failures: List[str] = list(inspection.get("errors", []))
    if not inspection.get("document_xml_exists"):
        failures.append(f"{DOCUMENT_XML} missing")
    if inspection.get("document_xml_exists") and not inspection.get("document_xml_parseable"):
        failures.append(f"{DOCUMENT_XML} not parseable")

    if classification == "supported":
        if not inspection.get("basic_omml_structure_present"):
            failures.append("no OMML structure found")
        if not inspection.get("basic_omml_structure_valid"):
            failures.append("basic OMML structure is not valid")
        failures.extend(_validate_flags(case, inspection))
        failures.extend(_validate_counts(case, inspection))
        failures.extend(_validate_summaries(case, inspection))

    result["failures"] = failures
    result["status"] = "passed" if not failures else "failed"
    if result["status"] == result["expected_status"]:
        result["result"] = "passed" if result["status"] == "passed" else "expected_failed"
    else:
        result["result"] = "unexpected_failed"
        if result["status"] == "passed" and result["expected_status"] == "failed":
            result["failures"] = ["expected status failed, found passed"]
    return result


def validate_inventory(inventory_path: Path) -> Dict[str, Any]:
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("inventory cases must be a list")

    results = [validate_case(case, inventory_path) for case in cases if isinstance(case, dict)]
    passed = sum(1 for item in results if item["result"] == "passed")
    expected_failed = sum(1 for item in results if item["result"] == "expected_failed")
    unexpected_failed = sum(1 for item in results if item["result"] == "unexpected_failed")
    skipped = sum(1 for item in results if item["result"] == "skipped")
    return {
        "schema_version": SCHEMA_VERSION,
        "inventory_path": str(inventory_path),
        "case_count": len(results),
        "passed_count": passed,
        "expected_failed_count": expected_failed,
        "unexpected_failed_count": unexpected_failed,
        "failed_count": expected_failed + unexpected_failed,
        "skipped_count": skipped,
        "cases": results,
    }


def render_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Modern DOCX + OMML validation")
    lines.append(f"Inventory: {report['inventory_path']}")
    lines.append(
        "Summary: "
        f"passed={report['passed_count']} "
        f"expected_failed={report['expected_failed_count']} "
        f"unexpected_failed={report['unexpected_failed_count']} "
        f"skipped={report['skipped_count']}"
    )
    lines.append("")
    for case in report.get("cases", []):
        inspection = case.get("inspection") if isinstance(case.get("inspection"), dict) else {}
        lines.append(
            f"- {case.get('case_id', '')}: {case.get('result', '')} "
            f"status={case.get('status', '')} expected={case.get('expected_status', '')} "
            f"path={inspection.get('file_path', case.get('source_docx', ''))}"
        )
        if inspection:
            lines.append(
                "  "
                f"document_xml={bool(inspection.get('document_xml_exists'))} "
                f"parseable={bool(inspection.get('document_xml_parseable'))} "
                f"oMath={inspection.get('omath_count', 0)} "
                f"oMathPara={inspection.get('omathpara_count', 0)} "
                f"inline_oMath={inspection.get('inline_omath_count', 0)} "
                f"inline={bool(inspection.get('appears_inline_math'))} "
                f"block={bool(inspection.get('appears_block_math'))} "
                f"omml={bool(inspection.get('basic_omml_structure_present'))}"
            )
        for failure in case.get("failures", []):
            lines.append(f"  failure: {failure}")
    return "\n".join(lines)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the modern DOCX + OMML regression inventory by inspecting word/document.xml."
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help=f"Regression inventory JSON. Default: {DEFAULT_INVENTORY}",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    report = validate_inventory(args.inventory.resolve())
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 1 if report["unexpected_failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
