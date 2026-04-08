#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def severity_rank(severity: str) -> int:
    return {"info": 0, "warning": 1, "error": 2, "blocker": 3}.get(str(severity).lower(), -1)


def max_issue_severity_by_code(answer_issues: List[Dict[str, Any]]) -> Dict[str, str]:
    buckets: Dict[str, str] = {}
    for issue in answer_issues:
        code = str(issue.get("code", ""))
        severity = str(issue.get("severity", "warning")).lower()
        if not code:
            continue
        current = buckets.get(code)
        if current is None or severity_rank(severity) > severity_rank(current):
            buckets[code] = severity
    return buckets


def run_command(cmd: List[str]) -> Tuple[int, str]:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output


def evaluate_expected(
    *,
    expected: Dict[str, Any],
    exam_bundle: Dict[str, Any],
    question_bank_items: Dict[str, Any],
    qa: Dict[str, Any],
) -> List[str]:
    failures: List[str] = []
    items = question_bank_items.get("items", [])
    question = items[0] if isinstance(items, list) and items else {}
    answer_key = question.get("answer_key", {}) if isinstance(question, dict) else {}
    reconciliation = question.get("reconciliation", {}) if isinstance(question, dict) else {}
    answer_summary = exam_bundle.get("answer_summary", {}) if isinstance(exam_bundle, dict) else {}

    if "answer_summary_present" in expected:
        actual_present = bool(answer_summary.get("present"))
        if actual_present != bool(expected.get("answer_summary_present")):
            failures.append(
                f"answer_summary.present mismatch: expected={bool(expected.get('answer_summary_present'))} actual={actual_present}"
            )

    if "answer_mode" in expected:
        actual_mode = str(answer_key.get("mode", ""))
        if actual_mode != str(expected.get("answer_mode")):
            failures.append(f"answer_key.mode mismatch: expected={expected.get('answer_mode')} actual={actual_mode}")

    if "reconciliation_status" in expected:
        actual_status = str(reconciliation.get("status", ""))
        if actual_status != str(expected.get("reconciliation_status")):
            failures.append(
                f"reconciliation.status mismatch: expected={expected.get('reconciliation_status')} actual={actual_status}"
            )

    if "chosen_source" in expected:
        actual_source = str(reconciliation.get("chosen_source", ""))
        if actual_source != str(expected.get("chosen_source")):
            failures.append(f"reconciliation.chosen_source mismatch: expected={expected.get('chosen_source')} actual={actual_source}")

    if "publish_verdict" in expected:
        actual_verdict = str(qa.get("publish_verdict", ""))
        if actual_verdict != str(expected.get("publish_verdict")):
            failures.append(f"publish_verdict mismatch: expected={expected.get('publish_verdict')} actual={actual_verdict}")

    answer_issues = qa.get("answer_qa_issues", [])
    answer_issue_codes = {str(issue.get("code", "")) for issue in answer_issues if isinstance(issue, dict)}
    required_codes = expected.get("required_issue_codes", [])
    if isinstance(required_codes, list):
        for code in required_codes:
            if str(code) not in answer_issue_codes:
                failures.append(f"required issue code not found: {code}")

    forbidden_codes = expected.get("forbidden_issue_codes", [])
    if isinstance(forbidden_codes, list):
        for code in forbidden_codes:
            if str(code) in answer_issue_codes:
                failures.append(f"forbidden issue code present: {code}")

    max_severity_policy = expected.get("max_issue_severity", {})
    if isinstance(max_severity_policy, dict):
        actual_max = max_issue_severity_by_code([issue for issue in answer_issues if isinstance(issue, dict)])
        for code, allowed in max_severity_policy.items():
            actual = actual_max.get(str(code))
            if actual is None:
                failures.append(f"max_issue_severity policy expects code '{code}' but no such issue was emitted")
                continue
            if severity_rank(actual) > severity_rank(str(allowed)):
                failures.append(f"issue severity too high for {code}: allowed<={allowed} actual={actual}")

    return failures


def render_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Answer Pipeline Regression Report")
    lines.append("")
    lines.append(f"- Run name: `{report.get('run_name', '')}`")
    lines.append(f"- Inventory: `{report.get('inventory_path', '')}`")
    lines.append(f"- Passed: `{report.get('passed_count', 0)}`")
    lines.append(f"- Failed: `{report.get('failed_count', 0)}`")
    lines.append("")
    lines.append("## Cases")
    lines.append("")
    for case in report.get("cases", []):
        case_id = str(case.get("case_id", ""))
        status = str(case.get("status", ""))
        lines.append(f"- `{case_id}`: `{status}`")
        failures = case.get("failures", [])
        if failures:
            for failure in failures:
                lines.append(f"  - {failure}")
        observed = case.get("observed", {})
        if isinstance(observed, dict):
            lines.append(
                "  - "
                + ", ".join(
                    [
                        f"mode={observed.get('answer_mode', '')}",
                        f"reconciliation={observed.get('reconciliation_status', '')}",
                        f"publish={observed.get('publish_verdict', '')}",
                    ]
                )
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dedicated answer pipeline regression group.")
    parser.add_argument("--inventory", type=Path, default=ROOT / "regression_set/answer_pipeline_inventory.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "out")
    parser.add_argument("--run-name", type=str, default="")
    parser.add_argument("--contract-gate-config", type=Path, default=ROOT / "scripts/contracts/contract_compatibility_v1.json")
    parser.add_argument("--enforce", action="store_true", default=True)
    parser.add_argument("--no-enforce", action="store_false", dest="enforce")
    args = parser.parse_args()

    inventory_path = args.inventory.resolve()
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"Invalid or empty answer pipeline inventory: {inventory_path}")

    run_name = args.run_name.strip() or f"answer-pipeline-regression-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = args.output_root.resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    qa_json_default = str(inventory.get("qa_json_default", "")).strip()
    generate_contract_script = ROOT / "scripts/contracts/generate_output_contract.py"
    contract_check_script = ROOT / "scripts/contracts/check_contract_compatibility.py"
    contract_gate_config = args.contract_gate_config.resolve()

    report_cases: List[Dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("case_id", "")).strip()
        fixture_html = str(case.get("fixture_html", "")).strip()
        case_dir = run_dir / "cases" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        result: Dict[str, Any] = {
            "case_id": case_id,
            "status": "failed",
            "failures": [],
            "artifacts": {},
        }

        if not case_id or not fixture_html:
            result["status"] = "error"
            result["failures"] = ["missing case_id or fixture_html"]
            report_cases.append(result)
            continue

        html_path = (ROOT / fixture_html).resolve()
        if not html_path.exists():
            result["status"] = "error"
            result["failures"] = [f"fixture_html not found: {html_path}"]
            report_cases.append(result)
            continue

        qa_json_rel = str(case.get("qa_json", qa_json_default)).strip()
        qa_json_path = (ROOT / qa_json_rel).resolve() if qa_json_rel else Path()
        if not qa_json_rel or not qa_json_path.exists():
            result["status"] = "error"
            result["failures"] = [f"qa_json not found: {qa_json_path}"]
            report_cases.append(result)
            continue

        override_manifest_rel = str(case.get("override_manifest", "")).strip()
        override_manifest_path = (ROOT / override_manifest_rel).resolve() if override_manifest_rel else None
        if override_manifest_path and not override_manifest_path.exists():
            result["status"] = "error"
            result["failures"] = [f"override_manifest not found: {override_manifest_path}"]
            report_cases.append(result)
            continue

        cmd = [
            sys.executable,
            str(generate_contract_script),
            "--html",
            str(html_path),
            "--qa-json",
            str(qa_json_path),
            "--out-dir",
            str(case_dir),
        ]
        subject = str(case.get("subject", "")).strip()
        if subject:
            cmd.extend(["--subject", subject])
        output_mode = str(case.get("output_mode", "")).strip()
        if output_mode:
            cmd.extend(["--output-mode", output_mode])
        if override_manifest_path:
            cmd.extend(["--override-manifest", str(override_manifest_path)])

        rc, output = run_command(cmd)
        (case_dir / "contract-build.log").write_text(output, encoding="utf-8")
        if rc != 0:
            result["status"] = "error"
            result["failures"] = [f"contract generation failed (exit={rc})"]
            report_cases.append(result)
            continue

        gate_cmd = [
            sys.executable,
            str(contract_check_script),
            "--contract-dir",
            str(case_dir),
            "--config",
            str(contract_gate_config),
            "--summary-json",
            str(case_dir / "contract-gate-summary.json"),
        ]
        gate_rc, gate_output = run_command(gate_cmd)
        (case_dir / "contract-gate.log").write_text(gate_output, encoding="utf-8")
        if gate_rc != 0:
            result["status"] = "error"
            result["failures"] = [f"contract compatibility failed (exit={gate_rc})"]
            report_cases.append(result)
            continue

        exam_bundle = read_json(case_dir / "exam_bundle.json")
        question_bank_items = read_json(case_dir / "question_bank_items.json")
        qa = read_json(case_dir / "qa.json")

        expected = case.get("expected", {}) if isinstance(case.get("expected", {}), dict) else {}
        failures = evaluate_expected(
            expected=expected,
            exam_bundle=exam_bundle,
            question_bank_items=question_bank_items,
            qa=qa,
        )

        items = question_bank_items.get("items", [])
        question = items[0] if isinstance(items, list) and items else {}
        observed = {
            "answer_summary_present": bool((exam_bundle.get("answer_summary", {}) or {}).get("present")),
            "answer_summary_source_type": str((exam_bundle.get("answer_summary", {}) or {}).get("source_type", "")),
            "answer_mode": str((question.get("answer_key", {}) or {}).get("mode", "")),
            "reconciliation_status": str((question.get("reconciliation", {}) or {}).get("status", "")),
            "chosen_source": str((question.get("reconciliation", {}) or {}).get("chosen_source", "")),
            "publish_verdict": str(qa.get("publish_verdict", "")),
            "answer_issue_codes": sorted(
                {
                    str(issue.get("code", ""))
                    for issue in (qa.get("answer_qa_issues", []) or [])
                    if isinstance(issue, dict) and issue.get("code")
                }
            ),
            "issue_max_severity": max_issue_severity_by_code(
                [issue for issue in (qa.get("answer_qa_issues", []) or []) if isinstance(issue, dict)]
            ),
        }

        result["status"] = "passed" if not failures else "failed"
        result["failures"] = failures
        result["expected"] = expected
        result["observed"] = observed
        result["artifacts"] = {
            "exam_bundle": str(case_dir / "exam_bundle.json"),
            "question_bank_items": str(case_dir / "question_bank_items.json"),
            "parser_report": str(case_dir / "parser_report.json"),
            "qa": str(case_dir / "qa.json"),
            "manifest": str(case_dir / "manifest.json"),
            "override_audit": str(case_dir / "override_audit.json"),
            "contract_gate_summary": str(case_dir / "contract-gate-summary.json"),
        }
        report_cases.append(result)

    failed_count = sum(1 for case in report_cases if case.get("status") != "passed")
    report = {
        "schema_version": "answer_pipeline_regression_result.v1",
        "run_name": run_name,
        "inventory_path": str(inventory_path),
        "run_dir": str(run_dir),
        "case_count": len(report_cases),
        "passed_count": len(report_cases) - failed_count,
        "failed_count": failed_count,
        "cases": report_cases,
    }
    write_json(run_dir / "answer-pipeline-regression-report.json", report)
    (run_dir / "answer-pipeline-regression-report.md").write_text(render_markdown(report), encoding="utf-8")

    if failed_count and args.enforce:
        raise SystemExit(1)

    print(str(run_dir))


if __name__ == "__main__":
    main()
