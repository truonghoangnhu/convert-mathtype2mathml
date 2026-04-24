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


def _case_status_index(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for case in report.get("case_statuses", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if case_id:
            index[case_id] = case
    return index


def _failed_structural_diff_index(report: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}
    for case in report.get("structural_diffs", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if not case_id:
            continue
        checks = [
            check
            for check in case.get("structural_checks", [])
            if isinstance(check, dict) and not bool(check.get("passed"))
        ]
        if checks:
            index[case_id] = checks
    return index


def _interesting_cases(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    failed_checks = _failed_structural_diff_index(report)
    case_statuses = _case_status_index(report)
    interesting: List[Dict[str, Any]] = []
    for case in report.get("patch_path_diagnostics", {}).get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if not case_id:
            continue
        drift_origin_hint = str(case.get("drift_origin_hint", "")).strip()
        has_drift = drift_origin_hint and drift_origin_hint != "no_structural_drift_detected"
        case_failed_checks = failed_checks.get(case_id, [])
        if not has_drift and not case_failed_checks:
            continue
        interesting.append(
            {
                "case_id": case_id,
                "gate_status": str(case_statuses.get(case_id, {}).get("gate_status", "unknown")),
                "structural_status": str(case_statuses.get(case_id, {}).get("structural_status", "unknown")),
                "drift_origin_hint": drift_origin_hint,
                "failed_checks": case_failed_checks,
                "patch_summary_record": case.get("patch_summary_record", {}) if isinstance(case.get("patch_summary_record"), dict) else {},
            }
        )
    for case_id, checks in failed_checks.items():
        if any(item["case_id"] == case_id for item in interesting):
            continue
        interesting.append(
            {
                "case_id": case_id,
                "gate_status": str(case_statuses.get(case_id, {}).get("gate_status", "unknown")),
                "structural_status": str(case_statuses.get(case_id, {}).get("structural_status", "unknown")),
                "drift_origin_hint": "",
                "failed_checks": checks,
                "patch_summary_record": {},
            }
        )
    return sorted(interesting, key=lambda item: item["case_id"])


def _serializer_only_cases(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    serializer_cases: List[Dict[str, Any]] = []
    for case in report.get("patch_path_diagnostics", {}).get("cases", []):
        if not isinstance(case, dict):
            continue
        if str(case.get("drift_class", "")).strip() != "serializer_only_drift":
            continue
        case_id = str(case.get("case_id", "")).strip()
        if not case_id:
            continue
        patch_summary = case.get("patch_summary_record", {}) if isinstance(case.get("patch_summary_record"), dict) else {}
        serializer_cases.append(
            {
                "case_id": case_id,
                "omml_preservation": str(patch_summary.get("omml_preservation", "")),
                "omml_drift_warning": str(patch_summary.get("omml_drift_warning", "")),
                "omml_drift_class": str(patch_summary.get("omml_drift_class", "")),
                "drift_origin_hint": str(case.get("drift_origin_hint", "")),
                "omml_before": str(patch_summary.get("omml_before", "")),
                "omml_after": str(patch_summary.get("omml_after", "")),
                "omml_drift_pair": str(patch_summary.get("omml_drift_pair", "")),
            }
        )
    return sorted(serializer_cases, key=lambda item: item["case_id"])


def _render_omml_attention_signal(patch_summary: Dict[str, Any]) -> str:
    preservation = str(patch_summary.get("omml_preservation", "")).strip()
    drift_class = str(patch_summary.get("omml_drift_class", "")).strip()
    drift_warning = str(patch_summary.get("omml_drift_warning", "")).strip()
    parts = [
        f"preservation={preservation or 'n/a'}",
        f"drift_class={drift_class or 'n/a'}",
        f"drift_warning={drift_warning or 'n/a'}",
    ]
    return " ".join(parts)


def _has_omml_attention_signal(patch_summary: Dict[str, Any]) -> bool:
    preservation = str(patch_summary.get("omml_preservation", "")).strip()
    drift_class = str(patch_summary.get("omml_drift_class", "")).strip()
    drift_warning = str(patch_summary.get("omml_drift_warning", "")).strip()
    return preservation.startswith("drift_") or bool(drift_class) or bool(drift_warning)


def render_summary_markdown(report: Dict[str, Any]) -> str:
    structural_summary = report.get("structural_summary", {})
    interesting_cases = _interesting_cases(report)
    serializer_only_cases = _serializer_only_cases(report)
    lines = [
        "## Modern DOCX + OMML Generated-Output Gate",
        "",
        f"- Overall gate result: `{report.get('overall_gate_result', 'unknown')}`",
        f"- Structural summary: `cases={structural_summary.get('case_count', 0)} passed={structural_summary.get('passed_count', 0)} expected_failed={structural_summary.get('expected_failed_count', 0)} unexpected_failed={structural_summary.get('unexpected_failed_count', 0)} skipped={structural_summary.get('skipped_count', 0)} structural_failed_checks={structural_summary.get('structural_failed_check_count', 0)}`",
        "",
    ]
    if not interesting_cases and not serializer_only_cases:
        lines.append("No failed or drifting cases.")
        return "\n".join(lines) + "\n"

    if interesting_cases:
        lines.extend(["### Failed Or Drifting Cases", ""])
        for case in interesting_cases:
            lines.append(f"- case_id: `{case['case_id']}`")
            lines.append(f"- gate_status: `{case['gate_status']}`")
            lines.append(f"- structural_status: `{case['structural_status']}`")
            if case["drift_origin_hint"]:
                lines.append(f"- drift_origin_hint: `{case['drift_origin_hint']}`")
            for check in case["failed_checks"]:
                lines.append(
                    f"- structural_diff: `{check.get('name', '')}` "
                    f"expected={check.get('expected')!r} actual={check.get('actual')!r}"
                )
            patch_summary = case["patch_summary_record"]
            if patch_summary and _has_omml_attention_signal(patch_summary):
                lines.append(f"- omml_attention: `{_render_omml_attention_signal(patch_summary)}`")
            for key in (
                "omml_before",
                "omml_after",
                "omml_drift_warning",
                "omml_drift_class",
                "omml_drift_pair",
                "omml_drift_bundle",
            ):
                value = patch_summary.get(key)
                if value not in (None, ""):
                    lines.append(f"- {key}: `{value}`")
            lines.append("")

    if serializer_only_cases:
        lines.extend(["### Serializer-Only Drift Cases", ""])
        for case in serializer_only_cases:
            lines.append(f"- case_id: `{case['case_id']}`")
            if _has_omml_attention_signal(case):
                lines.append(
                    "- omml_attention: "
                    f"`{_render_omml_attention_signal(case)}`"
                )
            if case["omml_drift_class"]:
                lines.append(f"- omml_drift_class: `{case['omml_drift_class']}`")
            if case["drift_origin_hint"]:
                lines.append(f"- drift_origin_hint: `{case['drift_origin_hint']}`")
            if case["omml_before"]:
                lines.append(f"- omml_before: `{case['omml_before']}`")
            if case["omml_after"]:
                lines.append(f"- omml_after: `{case['omml_after']}`")
            if case["omml_drift_pair"]:
                lines.append(f"- omml_drift_pair: `{case['omml_drift_pair']}`")
            lines.append("")
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
