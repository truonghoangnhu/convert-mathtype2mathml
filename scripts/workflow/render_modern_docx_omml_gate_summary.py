#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_REPORT = ROOT / "out" / "modern-docx-omml-generated" / "modern_docx_omml_generated_output_gate_report.json"


def _failed_cases(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    failed_cases: List[Dict[str, Any]] = []
    for case in report.get("structural_diffs", []):
        if not isinstance(case, dict):
            continue
        checks = [
            check
            for check in case.get("structural_checks", [])
            if isinstance(check, dict) and not bool(check.get("passed"))
        ]
        if checks:
            failed_cases.append({"case_id": case.get("case_id", ""), "checks": checks})
    return failed_cases


def render_summary_markdown(report: Dict[str, Any]) -> str:
    structural_summary = report.get("structural_summary", {})
    failed_cases = _failed_cases(report)
    lines = [
        "## Modern DOCX + OMML Generated-Output Gate",
        "",
        f"- Overall gate result: `{report.get('overall_gate_result', 'unknown')}`",
        f"- Structural summary: `cases={structural_summary.get('case_count', 0)} passed={structural_summary.get('passed_count', 0)} expected_failed={structural_summary.get('expected_failed_count', 0)} unexpected_failed={structural_summary.get('unexpected_failed_count', 0)} skipped={structural_summary.get('skipped_count', 0)} structural_failed_checks={structural_summary.get('structural_failed_check_count', 0)}`",
        "",
    ]
    if not failed_cases:
        lines.append("No failed structural diffs.")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "### Failed Structural Diffs",
            "",
            "| case_id | check | expected | actual |",
            "| --- | --- | --- | --- |",
        ]
    )
    for case in failed_cases:
        case_id = str(case.get("case_id", "")).replace("|", "\\|")
        for check in case["checks"]:
            name = str(check.get("name", "")).replace("|", "\\|")
            expected = repr(check.get("expected")).replace("|", "\\|")
            actual = repr(check.get("actual")).replace("|", "\\|")
            lines.append(f"| {case_id} | {name} | `{expected}` | `{actual}` |")
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the modern DOCX + OMML generated-output gate GitHub summary markdown."
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Generated-output gate report JSON. Default: {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--write-github-step-summary",
        action="store_true",
        help="Write markdown to the path in GITHUB_STEP_SUMMARY instead of stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    report_path = args.report.resolve()
    if not report_path.exists():
        raise SystemExit(f"report not found: {report_path}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"report JSON could not be parsed: {report_path} ({exc})") from exc
    markdown = render_summary_markdown(report)

    if args.write_github_step_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path:
            raise SystemExit("GITHUB_STEP_SUMMARY is not set")
        Path(summary_path).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
