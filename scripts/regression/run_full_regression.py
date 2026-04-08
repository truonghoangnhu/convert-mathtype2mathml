#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "full_regression_report.v1"
GROUP_ORDER = ["phase-b", "answer-pipeline", "docx-export"]

GROUP_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "phase-b": {
        "script": ROOT / "scripts/regression/run_phase_b_regression.py",
        "child_run_name": "phase-b",
        "report_json_rel": Path("baseline/performance-baseline.json"),
        "report_md_rel": Path("baseline/performance-baseline.md"),
    },
    "answer-pipeline": {
        "script": ROOT / "scripts/regression/run_answer_pipeline_regression.py",
        "child_run_name": "answer-pipeline",
        "report_json_rel": Path("answer-pipeline-regression-report.json"),
        "report_md_rel": Path("answer-pipeline-regression-report.md"),
    },
    "docx-export": {
        "script": ROOT / "scripts/regression/run_docx_export_regression.py",
        "child_run_name": "docx-export",
        "report_json_rel": Path("docx_export_regression_report.json"),
        "report_md_rel": Path("docx_export_regression_report.md"),
    },
}


def repo_root() -> Path:
    return ROOT


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(cmd: List[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    combined = (result.stdout or "") + (("\n" if result.stdout and result.stderr else "") + (result.stderr or ""))
    log_path.write_text(combined, encoding="utf-8")
    return int(result.returncode)


def safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_group_names(raw_groups: Sequence[str]) -> List[str]:
    if not raw_groups:
        return list(GROUP_ORDER)
    normalized = [str(item).strip() for item in raw_groups if str(item).strip()]
    if not normalized or any(item.lower() == "all" for item in normalized):
        return list(GROUP_ORDER)
    unknown = [item for item in normalized if item not in GROUP_DEFINITIONS]
    if unknown:
        raise SystemExit(f"Unknown regression group(s): {', '.join(unknown)}")
    ordered = [group for group in GROUP_ORDER if group in normalized]
    return ordered


def _count_status(items: Sequence[Dict[str, Any]], key: str = "status") -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        if isinstance(item, dict):
            counter[str(item.get(key, ""))] += 1
    return dict(counter)


def _first_existing_artifacts(paths: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, value in paths.items():
        if isinstance(value, (str, Path)) and str(value).strip():
            path = Path(str(value))
            if path.exists():
                result[key] = str(path)
    return result


def summarize_phase_b(report: Dict[str, Any]) -> Dict[str, Any]:
    samples = report.get("samples", [])
    if not isinstance(samples, list):
        samples = []
    gates = report.get("gates", {}) if isinstance(report.get("gates", {}), dict) else {}
    needs_review_count = int(report.get("needs_review_count", 0) or 0)

    sample_status_counts = _count_status([item for item in samples if isinstance(item, dict)])
    failed_samples = [item for item in samples if isinstance(item, dict) and str(item.get("status", "")) == "failed_gate"]
    parser_warning_samples: List[str] = []
    contract_warning_samples: List[str] = []
    parser_warning_count_total = 0
    contract_warning_count_total = 0
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        sample_id = str(sample.get("sample_id", ""))
        parser_warning_count = int(sample.get("parser_warning_count", 0) or 0)
        if parser_warning_count > 0:
            parser_warning_count_total += parser_warning_count
            parser_warning_samples.append(sample_id)
        contract_gate = sample.get("contract_gate", {})
        warnings = contract_gate.get("warnings", []) if isinstance(contract_gate, dict) else []
        if isinstance(warnings, list) and warnings:
            contract_warning_count_total += len(warnings)
            contract_warning_samples.append(sample_id)

    gate_failures = gates.get("failures", [])
    if not isinstance(gate_failures, list):
        gate_failures = []

    review_signals: List[str] = []
    if parser_warning_samples:
        review_signals.append(
            f"parser warnings in {len(set(parser_warning_samples))} sample(s)"
        )
    if contract_warning_samples:
        review_signals.append(
            f"contract warnings in {len(set(contract_warning_samples))} sample(s)"
        )
    review_findings = gates.get("review_findings", [])
    if isinstance(review_findings, list) and review_findings:
        review_signals.append(f"parser review findings in {len(review_findings)} item(s)")
    if needs_review_count > 0:
        review_signals.append(f"parser review-only samples in {needs_review_count} sample(s)")

    status = "passed"
    if failed_samples or gate_failures:
        status = "failed"
    elif review_signals:
        status = "passed_with_review"

    representative_artifacts: Dict[str, str] = {}
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        sample_artifacts = sample.get("artifacts", {})
        if isinstance(sample_artifacts, dict):
            representative_artifacts = _first_existing_artifacts(
                {
                    "html": sample_artifacts.get("html"),
                    "qa_json": sample_artifacts.get("qa_json"),
                    "qa_md": sample_artifacts.get("qa_md"),
                    "notes": sample_artifacts.get("notes"),
                    "parser_report": sample_artifacts.get("parser_report"),
                    "exam_bundle": sample_artifacts.get("exam_bundle"),
                    "question_bank_items": sample_artifacts.get("question_bank_items"),
                    "qa_contract": sample_artifacts.get("qa_contract"),
                    "override_audit": sample_artifacts.get("override_audit"),
                }
            )
            if representative_artifacts:
                break

    return {
        "status": status,
        "summary": {
            "sample_count": len(samples),
            "ok_count": int(report.get("ok_count", 0) or 0),
            "failed_count": int(report.get("failed_count", 0) or 0),
            "needs_review_count": needs_review_count,
            "sample_status_counts": sample_status_counts,
            "parser_gate_passed": bool(gates.get("parser_gate_passed", False)),
            "contract_gate_passed": bool(gates.get("contract_gate_passed", False)),
            "performance_gate_passed": bool(gates.get("performance_gate_passed", False)),
            "parser_warning_sample_count": len(set(parser_warning_samples)),
            "contract_warning_sample_count": len(set(contract_warning_samples)),
            "parser_warning_count_total": parser_warning_count_total,
            "contract_warning_count_total": contract_warning_count_total,
            "gate_failure_count": len(gate_failures),
            "category_aggregate": report.get("category_aggregate", {}),
        },
        "review_signals": review_signals,
        "caveats": [],
        "representative_artifacts": representative_artifacts,
        "child_report_verdict": "failed" if failed_samples or gate_failures else ("passed_with_review" if review_signals else "passed"),
    }


def summarize_answer_pipeline(report: Dict[str, Any]) -> Dict[str, Any]:
    cases = report.get("cases", [])
    if not isinstance(cases, list):
        cases = []
    case_status_counts = _count_status([item for item in cases if isinstance(item, dict)])
    publish_verdict_counts: Counter[str] = Counter()
    review_case_ids: List[str] = []
    manual_override_case_ids: List[str] = []

    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", ""))
        observed = case.get("observed", {})
        if not isinstance(observed, dict):
            observed = {}
        publish_verdict = str(observed.get("publish_verdict", ""))
        if publish_verdict:
            publish_verdict_counts[publish_verdict] += 1
        if publish_verdict in {"needs_review", "blocked"}:
            review_case_ids.append(case_id)
        chosen_source = str(observed.get("chosen_source", ""))
        if chosen_source == "manual_override":
            manual_override_case_ids.append(case_id)

    status = "passed"
    if int(report.get("failed_count", 0) or 0) > 0:
        status = "failed"
    elif review_case_ids:
        status = "passed_with_review"

    representative_artifacts: Dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_artifacts = case.get("artifacts", {})
        if isinstance(case_artifacts, dict):
            representative_artifacts = _first_existing_artifacts(
                {
                    "exam_bundle": case_artifacts.get("exam_bundle"),
                    "question_bank_items": case_artifacts.get("question_bank_items"),
                    "parser_report": case_artifacts.get("parser_report"),
                    "qa": case_artifacts.get("qa"),
                    "manifest": case_artifacts.get("manifest"),
                    "override_audit": case_artifacts.get("override_audit"),
                    "contract_gate_summary": case_artifacts.get("contract_gate_summary"),
                }
            )
            if representative_artifacts:
                break

    caveats: List[str] = []
    if review_case_ids:
        caveats.append(
            "answer pipeline includes review-target cases; canonical answers were produced with explicit review signals"
        )

    return {
        "status": status,
        "summary": {
            "case_count": len(cases),
            "passed_count": int(report.get("passed_count", 0) or 0),
            "failed_count": int(report.get("failed_count", 0) or 0),
            "case_status_counts": case_status_counts,
            "review_case_count": len(review_case_ids),
            "manual_override_case_count": len(manual_override_case_ids),
            "publish_verdict_counts": dict(publish_verdict_counts),
        },
        "review_signals": [f"review publish verdicts in {len(review_case_ids)} case(s)"] if review_case_ids else [],
        "caveats": caveats,
        "representative_artifacts": representative_artifacts,
        "child_report_verdict": "passed" if int(report.get("failed_count", 0) or 0) == 0 else "failed",
    }


def summarize_docx_export(report: Dict[str, Any]) -> Dict[str, Any]:
    cases = report.get("cases", [])
    if not isinstance(cases, list):
        cases = []
    case_status_counts = _count_status([item for item in cases if isinstance(item, dict)])
    review_case_ids: List[str] = []
    openability_false_case_ids: List[str] = []
    parity_ok_case_ids: List[str] = []
    parity_needs_review_case_ids: List[str] = []

    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", ""))
        status = str(case.get("status", ""))
        export_verdict = str(case.get("export_verdict", ""))
        parity_verdict = str(case.get("parity_verdict", ""))
        if status == "needs_review" or export_verdict == "needs_review" or parity_verdict == "needs_review":
            review_case_ids.append(case_id)
        if parity_verdict == "parity_ok":
            parity_ok_case_ids.append(case_id)
        if parity_verdict == "needs_review":
            parity_needs_review_case_ids.append(case_id)
        export_openability = case.get("export_openability", {})
        if isinstance(export_openability, dict) and not bool(export_openability.get("soffice_check_passed", False)):
            openability_false_case_ids.append(case_id)

    status = "passed"
    if int(report.get("failed_count", 0) or 0) > 0:
        status = "failed"
    elif review_case_ids:
        status = "passed_with_review"

    representative_artifacts: Dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_artifacts = case.get("artifacts", {})
        if isinstance(case_artifacts, dict):
            representative_artifacts = _first_existing_artifacts(
                {
                    "output_docx": case_artifacts.get("output_docx"),
                    "export_report": case_artifacts.get("export_report"),
                    "parity_report": case_artifacts.get("parity_report"),
                    "parity_report_md": case_artifacts.get("parity_report_md"),
                    "export_log": case_artifacts.get("export_log"),
                    "parity_log": case_artifacts.get("parity_log"),
                }
            )
            if representative_artifacts:
                break

    caveats: List[str] = []
    if openability_false_case_ids:
        caveats.append(
            "DOCX openability probe is environment-sensitive in this workspace; LibreOffice/soffice caveat remains visible"
        )

    return {
        "status": status,
        "summary": {
            "case_count": len(cases),
            "passed_count": int(report.get("passed_count", 0) or 0),
            "needs_review_count": int(report.get("needs_review_count", 0) or 0),
            "failed_count": int(report.get("failed_count", 0) or 0),
            "case_status_counts": case_status_counts,
            "openability_false_case_count": len(openability_false_case_ids),
            "parity_ok_case_count": len(parity_ok_case_ids),
            "parity_needs_review_case_count": len(parity_needs_review_case_ids),
        },
        "review_signals": [f"needs_review in {len(review_case_ids)} case(s)"] if review_case_ids else [],
        "caveats": caveats,
        "representative_artifacts": representative_artifacts,
        "child_report_verdict": str(report.get("verdict", "")) or "passed",
    }


def _group_status_sort(status: str) -> int:
    return {
        "passed": 0,
        "passed_with_review": 1,
        "skipped": 2,
        "failed": 3,
    }.get(status, 99)


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Full Regression Report")
    lines.append("")
    lines.append(f"- Run name: `{report.get('run_name', '')}`")
    lines.append(f"- Generated at: `{report.get('generated_at', '')}`")
    lines.append(f"- Output root: `{report.get('output_root', '')}`")
    lines.append(f"- Run dir: `{report.get('run_dir', '')}`")
    lines.append(f"- Selected groups: `{', '.join(report.get('selected_groups', []))}`")
    lines.append(f"- Executed groups: `{', '.join(report.get('executed_groups', []))}`")
    lines.append(f"- Overall verdict: `{report.get('overall_verdict', '')}`")
    lines.append("")
    lines.append("## Group Summary")
    lines.append("")
    lines.append("| group | status | exit | report | key metrics | caveats |")
    lines.append("|---|---|---:|---|---|---|")
    for group in report.get("groups", []):
        if not isinstance(group, dict):
            continue
        summary = group.get("summary", {}) if isinstance(group.get("summary", {}), dict) else {}
        report_json = group.get("report_json", "")
        key_metrics: List[str] = []
        if group.get("group_name") == "phase-b":
            key_metrics = [
                f"samples={summary.get('sample_count', 0)}",
                f"ok={summary.get('ok_count', 0)}",
                f"review={summary.get('needs_review_count', 0)}",
                f"failed={summary.get('failed_count', 0)}",
                f"parser={summary.get('parser_gate_passed', False)}",
                f"contract={summary.get('contract_gate_passed', False)}",
                f"perf={summary.get('performance_gate_passed', False)}",
            ]
        elif group.get("group_name") == "answer-pipeline":
            key_metrics = [
                f"cases={summary.get('case_count', 0)}",
                f"passed={summary.get('passed_count', 0)}",
                f"failed={summary.get('failed_count', 0)}",
                f"review={summary.get('review_case_count', 0)}",
            ]
        elif group.get("group_name") == "docx-export":
            key_metrics = [
                f"cases={summary.get('case_count', 0)}",
                f"passed={summary.get('passed_count', 0)}",
                f"review={summary.get('needs_review_count', 0)}",
                f"failed={summary.get('failed_count', 0)}",
                f"openability-false={summary.get('openability_false_case_count', 0)}",
            ]
        key_metrics_text = ", ".join(key_metrics)
        caveats = "; ".join(group.get("caveats", []))
        lines.append(
            f"| `{group.get('group_name', '')}` | `{group.get('status', '')}` | `{group.get('exit_code', '')}` | `{report_json}` | "
            f"`{key_metrics_text}` | {caveats} |"
        )
        for path_key, path_value in group.get("artifacts", {}).items():
            lines.append(f"  - {path_key}: `{path_value}`")
    lines.append("")
    lines.append("## Overall Summary")
    lines.append("")
    overall = report.get("overall", {}) if isinstance(report.get("overall", {}), dict) else {}
    lines.append(f"- Groups passed: `{overall.get('groups_passed', 0)}`")
    lines.append(f"- Groups passed with review: `{overall.get('groups_needs_review', 0)}`")
    lines.append(f"- Groups failed: `{overall.get('groups_failed', 0)}`")
    lines.append(f"- Groups skipped: `{overall.get('groups_skipped', 0)}`")
    lines.append(f"- Overall verdict: `{overall.get('overall_verdict', '')}`")
    if overall.get("hard_failures"):
        lines.append("")
        lines.append("### Hard Failures")
        for item in overall.get("hard_failures", []):
            lines.append(f"- {item}")
    if overall.get("review_signals"):
        lines.append("")
        lines.append("### Review Signals")
        for item in overall.get("review_signals", []):
            lines.append(f"- {item}")
    if overall.get("caveats"):
        lines.append("")
        lines.append("### Caveats")
        for item in overall.get("caveats", []):
            lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the unified regression entrypoint.")
    parser.add_argument(
        "--groups",
        nargs="*",
        default=[],
        help="Groups to run: phase-b, answer-pipeline, docx-export. Default: all.",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Optional run name. Defaults to timestamped full regression run.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "out",
        help="Root directory for regression artifacts.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first hard failure.",
    )
    args = parser.parse_args()

    selected_groups = resolve_group_names(args.groups)
    run_name = args.run_name.strip() or f"full-regression-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = args.output_root.resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    group_reports: List[Dict[str, Any]] = []
    hard_failure_seen = False

    for group_name in selected_groups:
        group_cfg = GROUP_DEFINITIONS[group_name]
        child_run_name = str(group_cfg["child_run_name"])
        child_run_dir = run_dir / child_run_name
        report_json_path = child_run_dir / str(group_cfg["report_json_rel"])
        report_md_path = child_run_dir / str(group_cfg["report_md_rel"])
        log_path = logs_dir / f"{group_name}.log"
        script = Path(group_cfg["script"])

        if hard_failure_seen and args.fail_fast:
            group_reports.append(
                {
                    "group_name": group_name,
                    "status": "skipped",
                    "exit_code": None,
                    "script": str(script),
                    "child_run_name": child_run_name,
                    "run_dir": str(child_run_dir),
                    "report_json": str(report_json_path),
                    "report_md": str(report_md_path),
                    "log_path": str(log_path),
                    "summary": {},
                    "review_signals": [],
                    "caveats": ["skipped because fail-fast stopped after an earlier hard failure"],
                    "artifacts": {},
                }
            )
            continue

        cmd = [
            sys.executable,
            str(script),
            "--output-root",
            str(run_dir),
            "--run-name",
            child_run_name,
        ]
        exit_code = run_command(cmd, cwd=repo_root(), log_path=log_path)

        report: Dict[str, Any] = safe_read_json(report_json_path)
        if group_name == "phase-b":
            group_result = summarize_phase_b(report)
        elif group_name == "answer-pipeline":
            group_result = summarize_answer_pipeline(report)
        elif group_name == "docx-export":
            group_result = summarize_docx_export(report)
        else:  # pragma: no cover - guarded by selection validation
            raise SystemExit(f"Unsupported group: {group_name}")

        group_status = group_result["status"]
        if exit_code != 0 or not report:
            if group_status != "skipped":
                group_status = "failed"
        if report and group_status != "failed":
            # Preserve a hard failure if the child report itself indicates one.
            if group_name == "phase-b":
                gates = report.get("gates", {}) if isinstance(report.get("gates", {}), dict) else {}
                if bool(report.get("failed_count", 0)) or bool(gates.get("failures")):
                    group_status = "failed"
            elif group_name == "answer-pipeline":
                if int(report.get("failed_count", 0) or 0) > 0:
                    group_status = "failed"
            elif group_name == "docx-export":
                if int(report.get("failed_count", 0) or 0) > 0:
                    group_status = "failed"

        if group_status == "failed":
            hard_failure_seen = True

        group_reports.append(
            {
                "group_name": group_name,
                "status": group_status,
                "exit_code": exit_code,
                "script": str(script),
                "child_run_name": child_run_name,
                "run_dir": str(child_run_dir),
                "report_json": str(report_json_path),
                "report_md": str(report_md_path),
                "log_path": str(log_path),
                "summary": group_result.get("summary", {}),
                "review_signals": group_result.get("review_signals", []),
                "caveats": group_result.get("caveats", []),
                "artifacts": group_result.get("representative_artifacts", {}),
                "child_report_verdict": group_result.get("child_report_verdict", ""),
            }
        )

    groups_passed = sum(1 for item in group_reports if item.get("status") == "passed")
    groups_needs_review = sum(1 for item in group_reports if item.get("status") == "passed_with_review")
    groups_failed = sum(1 for item in group_reports if item.get("status") == "failed")
    groups_skipped = sum(1 for item in group_reports if item.get("status") == "skipped")

    hard_failures: List[str] = []
    review_signals: List[str] = []
    caveats: List[str] = []
    for group in group_reports:
        status = str(group.get("status", ""))
        if status == "failed":
            hard_failures.append(f"{group.get('group_name', '')}: exit={group.get('exit_code', '')}")
        review_signals.extend([f"{group.get('group_name', '')}: {signal}" for signal in group.get("review_signals", [])])
        caveats.extend([f"{group.get('group_name', '')}: {note}" for note in group.get("caveats", [])])

    if groups_failed > 0:
        overall_verdict = "failed"
    elif groups_needs_review > 0:
        overall_verdict = "passed_with_review"
    else:
        overall_verdict = "passed"

    report = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "full_regression_report",
        "run_name": run_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "output_root": str(args.output_root.resolve()),
        "run_dir": str(run_dir),
        "selected_groups": selected_groups,
        "executed_groups": [group.get("group_name", "") for group in group_reports if group.get("status") != "skipped"],
        "fail_fast": bool(args.fail_fast),
        "groups": group_reports,
        "groups_passed": groups_passed,
        "groups_needs_review": groups_needs_review,
        "groups_failed": groups_failed,
        "groups_skipped": groups_skipped,
        "overall_verdict": overall_verdict,
        "overall": {
            "groups_passed": groups_passed,
            "groups_needs_review": groups_needs_review,
            "groups_failed": groups_failed,
            "groups_skipped": groups_skipped,
            "overall_verdict": overall_verdict,
            "hard_failures": hard_failures,
            "review_signals": review_signals,
            "caveats": caveats,
        },
        "verdict": overall_verdict,
    }

    report_json = run_dir / "full-regression-report.json"
    report_md = run_dir / "full-regression-report.md"
    write_json(report_json, report)
    report_md.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "run_name": run_name,
                "overall_verdict": overall_verdict,
                "groups_passed": groups_passed,
                "groups_needs_review": groups_needs_review,
                "groups_failed": groups_failed,
                "groups_skipped": groups_skipped,
                "report_json": str(report_json),
                "report_md": str(report_md),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 1 if overall_verdict == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
