#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "docx_export_regression.v1"


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(cmd: List[str], log_path: Path) -> Tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = (result.stdout or "") + (("\n" if result.stdout and result.stderr else "") + (result.stderr or ""))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    return result.returncode, output


def _safe_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
        return payload if isinstance(payload, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _report_counts(report: Dict[str, Any]) -> Dict[str, int]:
    return {
        "warnings_count": int(report.get("warnings_count", 0) or 0),
        "blockers_count": int(report.get("blockers_count", 0) or 0),
    }


def _case_status(export_report: Dict[str, Any], parity_report: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
    failures: List[str] = []
    warnings: List[str] = []

    export_blockers = int(export_report.get("blockers_count", 0) or 0)
    parity_blockers = int(parity_report.get("blockers_count", 0) or 0)
    export_warnings = int(export_report.get("warnings_count", 0) or 0)
    parity_warnings = int(parity_report.get("warnings_count", 0) or 0)

    if export_blockers > 0:
        failures.append(f"export blockers={export_blockers}")
    if parity_blockers > 0:
        failures.append(f"parity blockers={parity_blockers}")

    openability = export_report.get("openability", {}) if isinstance(export_report.get("openability"), dict) else {}
    if openability and openability.get("zip_integrity_checked") and not bool(openability.get("zip_integrity_passed")):
        failures.append("DOCX zip integrity failed")

    if export_warnings > 0:
        warnings.append(f"export warnings={export_warnings}")
    if parity_warnings > 0:
        warnings.append(f"parity warnings={parity_warnings}")

    if failures:
        return "failed", failures, warnings
    if warnings:
        return "needs_review", failures, warnings
    return "passed", failures, warnings


def _render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# DOCX Export Regression Report")
    lines.append("")
    lines.append(f"- Run: `{report.get('run_name', '')}`")
    lines.append(f"- Inventory: `{report.get('inventory_path', '')}`")
    lines.append(f"- Passed: `{report.get('passed_count', 0)}`")
    lines.append(f"- Needs review: `{report.get('needs_review_count', 0)}`")
    lines.append(f"- Failed: `{report.get('failed_count', 0)}`")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for case in report.get("cases", []):
        lines.append(
            f"- `{case.get('case_id', '')}`: `{case.get('status', '')}` "
            f"(export={case.get('export_verdict', '')}, parity={case.get('parity_verdict', '')})"
        )
        for failure in case.get("failures", []):
            lines.append(f"  - {failure}")
        for warning in case.get("warnings", []):
            lines.append(f"  - {warning}")
    lines.append("")
    return "\n".join(lines)


def run_case(
    *,
    case: Dict[str, Any],
    run_dir: Path,
    openability_timeout_sec: int,
) -> Dict[str, Any]:
    case_id = str(case.get("case_id", "")).strip()
    source_bundle_rel = str(case.get("source_bundle", "")).strip()
    output_docx_name = str(case.get("output_docx_name", f"{case_id}.docx")).strip() or f"{case_id}.docx"
    case_dir = run_dir / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    result: Dict[str, Any] = {
        "case_id": case_id,
        "status": "error",
        "failures": [],
        "warnings": [],
        "artifacts": {},
        "export_verdict": "",
        "parity_verdict": "",
        "export_counts": {},
        "parity_counts": {},
        "timings": {},
        "notes": list(case.get("notes", [])) if isinstance(case.get("notes", []), list) else [],
    }
    structural_failures: List[str] = []

    if not case_id or not source_bundle_rel:
        structural_failures.append("missing case_id or source_bundle")
        result["failures"] = structural_failures
        return result

    source_bundle = (ROOT / source_bundle_rel).resolve()
    if not source_bundle.exists():
        structural_failures.append(f"source bundle not found: {source_bundle}")
        result["failures"] = structural_failures
        return result

    output_docx = case_dir / output_docx_name
    export_report_path = case_dir / "docx_export_report.json"
    parity_report_path = case_dir / "docx_export_parity_report.json"
    parity_report_md_path = case_dir / "docx_export_parity_report.md"
    export_log = case_dir / "docx_export.log"
    parity_log = case_dir / "docx_export_parity.log"

    expected = case.get("expected", {})
    if not isinstance(expected, dict):
        expected = {}

    export_cmd = [
        sys.executable,
        str(ROOT / "scripts/export/docx_exporter.py"),
        str(source_bundle),
        str(output_docx),
        "--mode",
        "teacher_exam",
        "--report-path",
        str(export_report_path),
        "--check-openability",
        "--openability-timeout-sec",
        str(openability_timeout_sec),
    ]
    if bool(case.get("strict_math", False)):
        export_cmd.append("--strict-math")

    failure_policy_json = str(case.get("failure_policy_json", "")).strip()
    if failure_policy_json:
        policy_path = (ROOT / failure_policy_json).resolve()
        if policy_path.exists():
            export_cmd.extend(["--failure-policy-json", str(policy_path)])

    export_started = time.perf_counter()
    export_rc, _ = run_command(export_cmd, export_log)
    export_elapsed_ms = round((time.perf_counter() - export_started) * 1000.0, 3)

    export_report = _safe_report(export_report_path)
    export_report.setdefault("verdict", "blocked" if export_rc != 0 else "")
    result["export_verdict"] = str(export_report.get("verdict", ""))
    result["export_counts"] = _report_counts(export_report)
    result["timings"]["export_elapsed_ms"] = export_elapsed_ms

    result["artifacts"] = {
        "source_bundle": str(source_bundle),
        "output_docx": str(output_docx),
        "export_report": str(export_report_path),
        "parity_report": str(parity_report_path),
        "parity_report_md": str(parity_report_md_path),
        "export_log": str(export_log),
        "parity_log": str(parity_log),
    }

    parity_report: Dict[str, Any] = {}
    parity_rc = 0
    parity_elapsed_ms = 0.0
    if output_docx.exists() and result["export_verdict"] != "blocked":
        parity_cmd = [
            sys.executable,
            str(ROOT / "scripts/export/docx_export_parity.py"),
            "--exam-bundle",
            str(source_bundle),
            "--exported-docx",
            str(output_docx),
            "--out",
            str(parity_report_path),
            "--md-out",
            str(parity_report_md_path),
        ]
        parity_started = time.perf_counter()
        parity_rc, _ = run_command(parity_cmd, parity_log)
        parity_elapsed_ms = round((time.perf_counter() - parity_started) * 1000.0, 3)
        parity_report = _safe_report(parity_report_path)
        parity_report.setdefault("verdict", "blocked" if parity_rc != 0 else "")
    else:
        structural_failures.append("export did not produce a DOCX for parity review")

    result["parity_verdict"] = str(parity_report.get("verdict", ""))
    result["parity_counts"] = _report_counts(parity_report)
    result["timings"]["parity_elapsed_ms"] = parity_elapsed_ms

    status, failures, warnings = _case_status(export_report, parity_report)
    if export_rc != 0 and not export_report:
        failures.append(f"export command failed with exit={export_rc}")
    if parity_rc != 0 and output_docx.exists():
        warnings.append(f"parity command exited with {parity_rc}")

    expected_export_verdict = str(expected.get("export_verdict", "")).strip()
    if expected_export_verdict and str(export_report.get("verdict", "")) != expected_export_verdict:
        failures.append(
            f"export verdict mismatch: expected={expected_export_verdict} actual={export_report.get('verdict', '')}"
        )

    expected_parity_verdict = str(expected.get("parity_verdict", "")).strip()
    if expected_parity_verdict and str(parity_report.get("verdict", "")) != expected_parity_verdict:
        failures.append(
            f"parity verdict mismatch: expected={expected_parity_verdict} actual={parity_report.get('verdict', '')}"
        )

    if "openability_passed" in expected:
        actual_openability = bool((export_report.get("openability", {}) or {}).get("soffice_check_passed"))
        if bool(expected.get("openability_passed")) != actual_openability:
            failures.append(
                f"openability mismatch: expected={bool(expected.get('openability_passed'))} actual={actual_openability}"
            )

    failures = structural_failures + failures
    if failures:
        status = "failed"
    elif warnings:
        status = "needs_review"
    else:
        status = "passed"

    result["status"] = status
    result["failures"] = failures
    result["warnings"] = warnings
    result["export_openability"] = export_report.get("openability", {})
    result["parity_findings"] = parity_report.get("findings", [])
    result["timings"]["total_elapsed_ms"] = round(
        result["timings"].get("export_elapsed_ms", 0.0) + result["timings"].get("parity_elapsed_ms", 0.0),
        3,
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DOCX export regression set (Phase G).")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "regression_set/docx_export_inventory.json",
        help="Regression inventory JSON.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "out",
        help="Root directory for regression artifacts.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Optional run name (defaults to timestamped value).",
    )
    parser.add_argument(
        "--openability-timeout-sec",
        type=int,
        default=120,
        help="Timeout for DOCX openability round-trip in export mode.",
    )
    args = parser.parse_args()

    inventory_path = args.inventory.resolve()
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"Invalid regression inventory: {inventory_path}")

    run_name = args.run_name.strip() or f"docx-export-regression-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = args.output_root.resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    case_reports: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_reports.append(run_case(case=case, run_dir=run_dir, openability_timeout_sec=int(args.openability_timeout_sec)))

    passed_count = sum(1 for case in case_reports if case.get("status") == "passed")
    needs_review_count = sum(1 for case in case_reports if case.get("status") == "needs_review")
    failed_count = sum(1 for case in case_reports if case.get("status") == "failed")

    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "docx_export_regression_report",
        "run_name": run_name,
        "inventory_path": str(inventory_path),
        "output_root": str(run_dir),
        "case_count": len(case_reports),
        "passed_count": passed_count,
        "needs_review_count": needs_review_count,
        "failed_count": failed_count,
        "cases": case_reports,
        "verdict": "failed" if failed_count > 0 else "passed",
    }

    summary_json = run_dir / "docx_export_regression_report.json"
    summary_md = run_dir / "docx_export_regression_report.md"
    write_json(summary_json, summary)
    summary_md.write_text(_render_markdown(summary), encoding="utf-8")

    print(
        json.dumps(
            {
                "run_name": run_name,
                "passed_count": passed_count,
                "needs_review_count": needs_review_count,
                "failed_count": failed_count,
                "verdict": summary["verdict"],
                "report_json": str(summary_json),
                "report_md": str(summary_md),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
