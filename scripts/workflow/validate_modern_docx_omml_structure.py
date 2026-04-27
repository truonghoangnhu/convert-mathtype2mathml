#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, validate_inventory


def _check_failed(check: Dict[str, Any]) -> bool:
    return check.get("expected") is not None and not bool(check.get("passed"))


def _case_failed_checks(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        check
        for check in case.get("structural_checks", [])
        if isinstance(check, dict) and _check_failed(check)
    ]


def _augment_report(report: Dict[str, Any]) -> Dict[str, Any]:
    structural_checks = [
        check
        for case in report.get("cases", [])
        for check in case.get("structural_checks", [])
        if isinstance(check, dict)
    ]
    failed_checks = [check for check in structural_checks if _check_failed(check)]
    report["structural_check_count"] = len(structural_checks)
    report["structural_failed_check_count"] = len(failed_checks)
    return report


def render_structure_text(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Modern DOCX + OMML structural validation")
    lines.append(f"Inventory: {report['inventory_path']}")
    lines.append(
        "Summary: "
        f"cases={report['case_count']} "
        f"passed={report['passed_count']} "
        f"expected_failed={report['expected_failed_count']} "
        f"unexpected_failed={report['unexpected_failed_count']} "
        f"skipped={report['skipped_count']} "
        f"structural_failed_checks={report['structural_failed_check_count']}"
    )
    lines.append("")

    for case in report.get("cases", []):
        inspection = case.get("inspection") if isinstance(case.get("inspection"), dict) else {}
        failed_checks = _case_failed_checks(case)
        lines.append(
            f"- {case.get('case_id', '')}: {case.get('result', '')} "
            f"status={case.get('status', '')} expected={case.get('expected_status', '')} "
            f"path={inspection.get('file_path', case.get('target_docx', ''))}"
        )
        if inspection:
            lines.append(
                "  actual_counts: "
                f"oMath={inspection.get('omath_count', 0)} "
                f"oMathPara={inspection.get('omathpara_count', 0)} "
                f"inline_oMath={inspection.get('inline_omath_count', 0)}"
            )
            lines.append(f"  placement_summary: {inspection.get('placement_summary', '')}")
            lines.append(f"  paragraph_run_safety: {inspection.get('paragraph_run_safety_summary', '')}")
        if failed_checks:
            for check in failed_checks:
                expected = check.get("expected")
                expected_label = "<not set>" if expected is None else repr(expected)
                lines.append(
                    f"  check {check.get('name', '')}: fail "
                    f"actual={check.get('actual')!r} expected={expected_label}"
                )
        else:
            matched_checks = sum(
                1
                for check in case.get("structural_checks", [])
                if isinstance(check, dict) and check.get("expected") is not None
            )
            if matched_checks:
                lines.append(f"  structural_diff: all expected structural checks matched ({matched_checks} checks)")
        for failure in case.get("failures", []):
            lines.append(f"  failure: {failure}")
    return "\n".join(lines)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate generated modern DOCX + OMML output structure against expected invariants."
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=DEFAULT_INVENTORY,
        help=f"Inventory or generated-output manifest JSON. Default: {DEFAULT_INVENTORY}",
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
    report = _augment_report(validate_inventory(args.inventory.resolve()))
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_structure_text(report))
    return 1 if report["unexpected_failed_count"] or report["structural_failed_check_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
