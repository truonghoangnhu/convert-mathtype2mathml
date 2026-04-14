#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_REAL_CONTRACTS_ROOT = Path("out/full-corpus-in-test-validation-20260409-095900")
DEFAULT_FIXTURE_CASES_ROOT = Path("out/answer-pipeline-regression-20260409-133656/cases")
DEFAULT_FIXTURE_CASES = [
    "mc_local_summary_agree",
    "tf_summary_fill_missing_local",
    "short_answer_normalized_equivalent",
    "essay_rubric_marker",
    "no_summary_clear_local",
]

DEFAULT_OUTPUT_PARENT = Path("out")
DEFAULT_PILOT_PREFIX = "coverage-expansion-pilot"

DEFAULT_REVIEW_HOST = "127.0.0.1"
DEFAULT_REVIEW_PORT = 8120
DEFAULT_REVIEW_BOT = "coverage_pilot_bot"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(cmd: List[str], *, cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)


def _http_json(url: str, method: str = "GET", body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_server(url: str, process: subprocess.Popen[str], timeout_s: int = 45) -> None:
    deadline = time.time() + timeout_s
    last_error: Optional[str] = None
    while time.time() < deadline:
        if process.poll() is not None:
            stdout = ""
            if process.stdout is not None:
                stdout = process.stdout.read() or ""
            raise RuntimeError(f"review server exited early with code {process.returncode}\n{stdout}")
        try:
            _http_json(url)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(0.25)
    raise TimeoutError(f"review server did not become ready at {url}: {last_error or 'timeout'}")


def _find_jar(candidate: Optional[Path]) -> Path:
    if candidate is not None:
        jar = candidate.resolve()
        if not jar.exists():
            raise FileNotFoundError(f"java jar not found: {jar}")
        return jar
    matches = sorted(Path("target").glob("*-jar-with-dependencies.jar"))
    if matches:
        return matches[-1].resolve()
    raise FileNotFoundError("could not locate built jar under target/")


def _copy_bundle_dir(src: Path, dst_root: Path) -> Path:
    dst = dst_root / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def _discover_bundle_dirs(root: Path) -> List[Path]:
    if not root.exists():
        return []
    bundle_dirs: List[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if (child / "manifest.json").is_file() and (child / "question_bank_items.json").is_file():
            bundle_dirs.append(child)
    return bundle_dirs


def _rewrite_bundle_item_ids(bundle_dir: Path, *, prefix: str) -> Dict[str, Any]:
    """
    For pilot-only bundle co-existence in the same SQLite boundary DB:
    - ensure item_id values are unique across bundles (DB primary key is item_id)
    - keep the rest of the contract untouched (no business-logic edits)
    """
    qb_path = bundle_dir / "question_bank_items.json"
    payload = json.loads(qb_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{qb_path} must be a JSON object")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return {"bundle_dir": str(bundle_dir), "rewritten": False, "reason": "no items"}
    rewritten: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        old_id = str(item.get("item_id", "") or "").strip()
        if not old_id:
            continue
        new_id = f"{prefix}-{old_id}"
        if new_id != old_id:
            item["item_id"] = new_id
            rewritten.append({"old_item_id": old_id, "new_item_id": new_id})
    qb_path.write_text(_json(payload) + "\n", encoding="utf-8")
    return {"bundle_dir": str(bundle_dir), "rewritten": bool(rewritten), "rewrites": rewritten}


def _required_pending_question_ids(queue_payload: Dict[str, Any]) -> List[str]:
    items = queue_payload.get("items", [])
    if not isinstance(items, list):
        return []
    pending: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("required") is not True:
            continue
        qid = str(item.get("question_id", "") or "").strip()
        status = str(item.get("review_status", "") or "").strip()
        if not qid:
            continue
        if status in {"reviewed_fixed", "reviewed_confirmed", "auto_accepted"}:
            continue
        pending.append(qid)
    return pending


@dataclass
class FinalizeResult:
    bundle_id: str
    display_title: str
    subject: str
    question_count: int
    required_pending_before: int
    required_pending_confirmed: int
    finalize_allowed: bool
    finalize_status: str
    finalize_blockers: List[Dict[str, Any]]
    artifacts: Dict[str, str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "display_title": self.display_title,
            "subject": self.subject,
            "question_count": self.question_count,
            "required_pending_before": self.required_pending_before,
            "required_pending_confirmed": self.required_pending_confirmed,
            "finalize_allowed": self.finalize_allowed,
            "finalize_status": self.finalize_status,
            "finalize_blockers": self.finalize_blockers,
            "artifacts": self.artifacts,
        }


def _auto_confirm_required_questions(
    *,
    base_url: str,
    bundle_id: str,
    question_ids: List[str],
    reviewer: str,
    note: str,
) -> int:
    confirmed = 0
    for qid in question_ids:
        body = {
            "review_status": "reviewed_confirmed",
            "review_note": note,
            "reviewed_by": reviewer,
            "reviewer": reviewer,
            "edits": {},
        }
        _http_json(f"{base_url}/api/review/session/{bundle_id}/question/{qid}/save", method="POST", body=body)
        confirmed += 1
    return confirmed


def _finalize_all_bundles(
    *,
    review_root: Path,
    jar_path: Path,
    host: str,
    port: int,
    reviewer: str,
) -> Tuple[str, List[FinalizeResult]]:
    server_cmd = [
        "java",
        "-jar",
        str(jar_path),
        "review-server",
        "--review-root",
        str(review_root),
        "--host",
        host,
        "--port",
        str(port),
    ]
    server = subprocess.Popen(  # noqa: S603
        server_cmd,
        cwd=str(Path.cwd()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "JAVA_TOOL_OPTIONS": os.environ.get("JAVA_TOOL_OPTIONS", "")},
    )
    base_url = f"http://{host}:{port}"
    results: List[FinalizeResult] = []
    try:
        _wait_for_server(f"{base_url}/api/review/bundles", server)
        bundles_payload = _http_json(f"{base_url}/api/review/bundles")
        bundles = bundles_payload.get("bundles", []) if isinstance(bundles_payload.get("bundles"), list) else []

        for bundle in bundles:
            if not isinstance(bundle, dict):
                continue
            bundle_id = str(bundle.get("bundle_id", "") or "").strip()
            if not bundle_id:
                continue
            display_title = str(bundle.get("display_title", "") or "").strip()
            subject = str(bundle.get("subject", "") or "").strip()
            question_count = int(bundle.get("question_count", 0) or 0)

            queue = _http_json(
                f"{base_url}/api/review/session/{bundle_id}/queue?includeSecondary=true&includeReviewed=true&includeAll=true"
            )
            required_pending_before = int(queue.get("required_pending_count", 0) or 0)
            required_pending_ids = _required_pending_question_ids(queue)

            note = "coverage-expansion pilot: auto-confirm required item to allow finalize; no content edits"
            confirmed = _auto_confirm_required_questions(
                base_url=base_url,
                bundle_id=bundle_id,
                question_ids=required_pending_ids,
                reviewer=reviewer,
                note=note,
            )

            finalize = _http_json(
                f"{base_url}/api/review/session/{bundle_id}/finalize",
                method="POST",
                body={"finalized_by": reviewer, "finalize_note": "coverage-expansion pilot finalize (no content edits)"},
            )
            results.append(
                FinalizeResult(
                    bundle_id=bundle_id,
                    display_title=display_title,
                    subject=subject,
                    question_count=question_count,
                    required_pending_before=required_pending_before,
                    required_pending_confirmed=confirmed,
                    finalize_allowed=bool(finalize.get("allowed", False)),
                    finalize_status=str(finalize.get("status", "") or ""),
                    finalize_blockers=finalize.get("blockers", []) if isinstance(finalize.get("blockers"), list) else [],
                    artifacts=finalize.get("artifacts", {}) if isinstance(finalize.get("artifacts"), dict) else {},
                )
            )
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    return base_url, results


def _run_import_boundary(
    *,
    review_root: Path,
    output_root: Path,
    import_mode: str,
) -> Dict[str, Any]:
    db_path = output_root / "question_bank_import.sqlite"
    batch_report_json = output_root / "question_bank_batch_import_summary.json"
    batch_summary_md = output_root / "question_bank_batch_import_summary.md"
    cmd = [
        sys.executable,
        "-m",
        "question_bank",
        "--batch-root",
        str(review_root),
        "--db",
        str(db_path),
        "--mode",
        import_mode,
        "--batch-report-json",
        str(batch_report_json),
        "--batch-summary-md",
        str(batch_summary_md),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"import boundary failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not batch_report_json.exists():
        raise FileNotFoundError(f"batch import summary not written: {batch_report_json}")
    summary = _read_json(batch_report_json)
    return {
        "db_path": str(db_path.resolve()),
        "batch_report_json": str(batch_report_json.resolve()),
        "batch_summary_md": str(batch_summary_md.resolve()),
        "summary": summary,
    }


def _query_db_coverage(db_path: Path) -> Dict[str, Any]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        subject_readiness = [dict(row) for row in conn.execute(
            "SELECT subject, import_readiness, COUNT(*) AS count "
            "FROM approved_questions GROUP BY subject, import_readiness ORDER BY subject, import_readiness"
        ).fetchall()]
        approved_by_subject = [dict(row) for row in conn.execute(
            "SELECT subject, COUNT(*) AS count "
            "FROM approved_questions WHERE import_readiness='approved_importable' GROUP BY subject ORDER BY count DESC"
        ).fetchall()]
        approved_by_type = [dict(row) for row in conn.execute(
            "SELECT subject, question_type, COUNT(*) AS count "
            "FROM approved_questions WHERE import_readiness='approved_importable' "
            "GROUP BY subject, question_type ORDER BY subject, count DESC"
        ).fetchall()]
        approved_rubric = [dict(row) for row in conn.execute(
            "SELECT q.subject, COUNT(*) AS count "
            "FROM approved_questions q "
            "JOIN approved_question_rubrics r ON r.item_id=q.item_id "
            "WHERE q.import_readiness='approved_importable' AND COALESCE(r.rubric_text,'')!='' "
            "GROUP BY q.subject ORDER BY count DESC"
        ).fetchall()]
        approved_total = conn.execute(
            "SELECT COUNT(*) FROM approved_questions WHERE import_readiness='approved_importable'"
        ).fetchone()[0]
        return {
            "subject_readiness_counts": subject_readiness,
            "approved_item_total": int(approved_total),
            "approved_items_by_subject": approved_by_subject,
            "approved_items_by_question_type": approved_by_type,
            "approved_rubric_counts": approved_rubric,
        }
    finally:
        conn.close()


def _load_approved_item_ids(db_path: Path, *, subject: Optional[str] = None) -> List[str]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if subject:
            rows = conn.execute(
                "SELECT item_id FROM approved_questions WHERE import_readiness='approved_importable' AND subject=? ORDER BY bundle_id ASC, question_number ASC, item_id ASC",
                (subject,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT item_id FROM approved_questions WHERE import_readiness='approved_importable' ORDER BY subject ASC, bundle_id ASC, question_number ASC, item_id ASC"
            ).fetchall()
        return [str(row["item_id"]) for row in rows if row and row["item_id"]]
    finally:
        conn.close()


def _run_assembly_preview_export_verify(
    *,
    pilot_root: Path,
    db_path: Path,
    item_ids: List[str],
    seed: str,
) -> List[Dict[str, Any]]:
    if not item_ids:
        return []

    runs: List[Dict[str, Any]] = []
    assembly_dir = pilot_root / "assembled"
    assembly_dir.mkdir(parents=True, exist_ok=True)

    fixed_json = assembly_dir / "coverage_fixed_exam_assembly.json"
    fixed_md = assembly_dir / "coverage_fixed_exam_assembly.md"
    fixed_cmd = [
        sys.executable,
        "scripts/question_bank_assemble.py",
        "--db",
        str(db_path),
        "--mode",
        "fixed",
        "--title",
        "Coverage Expansion Fixed Assembly",
        "--output-json",
        str(fixed_json),
        "--output-md",
        str(fixed_md),
    ]
    for item_id in item_ids:
        fixed_cmd.extend(["--item-id", item_id])
    fixed_result = _run(fixed_cmd)
    if fixed_result.returncode != 0:
        runs.append(
            {
                "stage": "assemble_fixed",
                "ok": False,
                "returncode": fixed_result.returncode,
                "stdout": fixed_result.stdout,
                "stderr": fixed_result.stderr,
            }
        )
        return runs

    random_json = assembly_dir / "coverage_random_exam_assembly.json"
    random_md = assembly_dir / "coverage_random_exam_assembly.md"
    required_count = min(3, len(item_ids))
    random_cmd = [
        sys.executable,
        "scripts/question_bank_assemble.py",
        "--db",
        str(db_path),
        "--mode",
        "random",
        "--required-count",
        str(required_count),
        "--seed",
        seed,
        "--subject",
        "math",
        "--title",
        "Coverage Expansion Random Assembly",
        "--output-json",
        str(random_json),
        "--output-md",
        str(random_md),
    ]
    random_result = _run(random_cmd)
    if random_result.returncode != 0:
        runs.append(
            {
                "stage": "assemble_random",
                "ok": False,
                "returncode": random_result.returncode,
                "stdout": random_result.stdout,
                "stderr": random_result.stderr,
            }
        )
        return runs

    for artifact_path, label in [(fixed_json, "fixed"), (random_json, "random")]:
        artifact_path = artifact_path.resolve()
        for mode in ["student", "teacher"]:
            preview_json = artifact_path.with_name(f"{artifact_path.stem}.{mode}.preview.json")
            preview_md = artifact_path.with_name(f"{artifact_path.stem}.{mode}.preview.md")
            preview_html = artifact_path.with_name(f"{artifact_path.stem}.{mode}.preview.html")
            preview_cmd = [
                sys.executable,
                "scripts/question_bank_preview.py",
                "--artifact",
                str(artifact_path),
                "--mode",
                mode,
                "--output-json",
                str(preview_json),
                "--output-md",
                str(preview_md),
                "--output-html",
                str(preview_html),
            ]
            preview_result = _run(preview_cmd)
            if preview_result.returncode != 0:
                runs.append(
                    {
                        "assembly": label,
                        "mode": mode,
                        "stage": "preview",
                        "ok": False,
                        "returncode": preview_result.returncode,
                        "stdout": preview_result.stdout,
                        "stderr": preview_result.stderr,
                    }
                )
                continue

            docx_path = artifact_path.with_name(f"{artifact_path.stem}.{mode}.docx")
            export_report = artifact_path.with_name(f"{artifact_path.stem}.{mode}.export_report.json")
            export_cmd = [
                sys.executable,
                "scripts/question_bank_export_assembled_docx.py",
                "--artifact",
                str(artifact_path),
                "--mode",
                mode,
                "--output-docx",
                str(docx_path),
                "--report",
                str(export_report),
            ]
            export_result = _run(export_cmd)
            if not export_report.exists():
                runs.append(
                    {
                        "assembly": label,
                        "mode": mode,
                        "stage": "export",
                        "ok": False,
                        "returncode": export_result.returncode,
                        "stdout": export_result.stdout,
                        "stderr": export_result.stderr,
                        "error": "export report was not written",
                    }
                )
                continue

            acceptance_json = artifact_path.with_name(f"{artifact_path.stem}.{mode}.acceptance.json")
            acceptance_md = artifact_path.with_name(f"{artifact_path.stem}.{mode}.acceptance.md")
            verify_cmd = [
                sys.executable,
                "scripts/question_bank_verify_assembled_docx_export.py",
                "--artifact",
                str(artifact_path),
                "--export-report",
                str(export_report),
                "--docx",
                str(docx_path),
                "--output-json",
                str(acceptance_json),
                "--output-md",
                str(acceptance_md),
            ]
            verify_result = _run(verify_cmd)
            if not acceptance_json.exists():
                runs.append(
                    {
                        "assembly": label,
                        "mode": mode,
                        "stage": "verify",
                        "ok": False,
                        "returncode": verify_result.returncode,
                        "stdout": verify_result.stdout,
                        "stderr": verify_result.stderr,
                        "error": "acceptance report was not written",
                    }
                )
                continue

            export_payload = _read_json(export_report)
            acceptance_payload = _read_json(acceptance_json)
            runs.append(
                {
                    "assembly": label,
                    "mode": mode,
                    "assembly_artifact": str(artifact_path),
                    "preview_html": str(preview_html),
                    "docx_path": str(docx_path),
                    "export_report": str(export_report),
                    "export_verdict": export_payload.get("verdict"),
                    "acceptance_report": str(acceptance_json),
                    "acceptance_verdict": acceptance_payload.get("verdict"),
                    "export_warnings": int(export_payload.get("warnings_count", 0) or 0),
                    "export_blockers": int(export_payload.get("blockers_count", 0) or 0),
                    "acceptance_warnings": int((acceptance_payload.get("warnings_count") or 0) or 0),
                    "acceptance_blockers": int((acceptance_payload.get("blockers_count") or 0) or 0),
                }
            )

    return runs


def _render_pilot_report_md(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Assembled Exam Export v1 Coverage-Expansion Pilot Report")
    lines.append("")
    lines.append(f"- Generated at: `{report.get('generated_at','')}`")
    lines.append(f"- Pilot root: `{report.get('pilot_root','')}`")
    lines.append(f"- Review root: `{report.get('review_root','')}`")
    lines.append(f"- SQLite boundary DB: `{report.get('db_path','')}`")
    lines.append("")
    gaps = report.get("coverage_gaps", [])
    if gaps:
        lines.append("## Coverage Gaps (Summary)")
        for gap in gaps:
            if isinstance(gap, dict):
                lines.append(f"- `{gap.get('code','')}`: {gap.get('message','')}")
            else:
                lines.append(f"- {gap}")
        lines.append("")

    lines.append("## Import Coverage")
    coverage = report.get("db_coverage", {}) if isinstance(report.get("db_coverage"), dict) else {}
    lines.append(f"- approved_item_total: `{coverage.get('approved_item_total', 0)}`")
    lines.append("")
    lines.append("### Subject/Readiness Counts")
    lines.append("| subject | readiness | count |")
    lines.append("| --- | --- | ---: |")
    for row in coverage.get("subject_readiness_counts", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"| {row.get('subject','')} | {row.get('import_readiness','')} | {row.get('count',0)} |")
    lines.append("")

    lines.append("### Approved Items By Subject")
    lines.append("| subject | approved_count |")
    lines.append("| --- | ---: |")
    for row in coverage.get("approved_items_by_subject", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"| {row.get('subject','')} | {row.get('count',0)} |")
    lines.append("")

    lines.append("### Approved Rubric Counts")
    lines.append("| subject | rubric_count |")
    lines.append("| --- | ---: |")
    for row in coverage.get("approved_rubric_counts", []):
        if not isinstance(row, dict):
            continue
        lines.append(f"| {row.get('subject','')} | {row.get('count',0)} |")
    lines.append("")

    runs = report.get("runs", []) if isinstance(report.get("runs"), list) else []
    if runs:
        lines.append("## Assembly/Export Runs")
        verdicts = report.get("run_verdict_counts", {}) if isinstance(report.get("run_verdict_counts"), dict) else {}
        if verdicts:
            lines.append(f"- export verdicts: `{verdicts.get('export_verdicts', {})}`")
            lines.append(f"- acceptance verdicts: `{verdicts.get('acceptance_verdicts', {})}`")
            if verdicts.get("acceptance_issue_code_counts"):
                lines.append(f"- acceptance blocker codes: `{verdicts.get('acceptance_issue_code_counts')}`")
            lines.append("")
        lines.append("| assembly | mode | export_verdict | acceptance_verdict | docx |")
        lines.append("| --- | --- | --- | --- | --- |")
        for run in runs:
            if not isinstance(run, dict):
                continue
            lines.append(
                "| {assembly} | {mode} | {export_verdict} | {acceptance_verdict} | `{docx}` |".format(
                    assembly=str(run.get("assembly", "")),
                    mode=str(run.get("mode", "")),
                    export_verdict=str(run.get("export_verdict", "")),
                    acceptance_verdict=str(run.get("acceptance_verdict", "")),
                    docx=str(run.get("docx_path", "")),
                )
            )
        lines.append("")

    rec = report.get("recommendation", {})
    if isinstance(rec, dict) and rec:
        lines.append("## Recommendation")
        lines.append(f"- verdict: `{rec.get('verdict','')}`")
        if rec.get("message"):
            lines.append(f"- note: {rec.get('message','')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a coverage-expansion pilot for assembled-exam export v1 (no runtime logic changes).")
    parser.add_argument("--real-contracts-root", type=Path, default=DEFAULT_REAL_CONTRACTS_ROOT, help="Directory containing real bundle contract dirs (manifest.json + question_bank_items.json)")
    parser.add_argument("--fixture-cases-root", type=Path, default=DEFAULT_FIXTURE_CASES_ROOT, help="Directory containing fixture case bundle dirs")
    parser.add_argument("--fixture-case", action="append", default=[], help="Fixture case dir name (repeatable). Defaults to the standard answer-pipeline cases.")
    parser.add_argument("--output-parent", type=Path, default=DEFAULT_OUTPUT_PARENT, help="Output parent directory (default: out/)")
    parser.add_argument("--jar", type=Path, default=None, help="Path to the built converter jar (for review-server)")
    parser.add_argument("--review-port", type=int, default=DEFAULT_REVIEW_PORT, help="Review server port")
    parser.add_argument("--reviewer", type=str, default=DEFAULT_REVIEW_BOT, help="Reviewer/finalizer identity recorded in review artifacts")
    parser.add_argument("--import-mode", type=str, default="allow-draft", choices=["approved-only", "allow-draft"], help="question_bank import mode")
    args = parser.parse_args(argv)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    pilot_root = (args.output_parent / f"{DEFAULT_PILOT_PREFIX}-{ts}").resolve()
    review_root = (pilot_root / "review_root").resolve()
    pilot_root.mkdir(parents=True, exist_ok=True)
    review_root.mkdir(parents=True, exist_ok=True)

    fixture_cases = args.fixture_case or list(DEFAULT_FIXTURE_CASES)
    jar_path = _find_jar(args.jar)

    # Seed bundles for this pilot run (copy to an isolated review_root so we never mutate source bundles).
    real_sources = _discover_bundle_dirs(args.real_contracts_root.resolve())
    fixture_sources = []
    for case in fixture_cases:
        src = (args.fixture_cases_root / case).resolve()
        if src.is_dir() and (src / "manifest.json").is_file() and (src / "question_bank_items.json").is_file():
            fixture_sources.append(src)

    copied_real = [_copy_bundle_dir(src, review_root) for src in real_sources]
    copied_fixture = [_copy_bundle_dir(src, review_root) for src in fixture_sources]

    fixture_rewrites: List[Dict[str, Any]] = []
    for bundle_dir in copied_fixture:
        # The answer-pipeline fixtures reuse the same item_id across cases; rewrite ids so they can co-exist in one DB.
        try:
            fixture_rewrites.append(_rewrite_bundle_item_ids(bundle_dir, prefix=bundle_dir.name))
        except Exception as exc:  # noqa: BLE001
            fixture_rewrites.append({"bundle_dir": str(bundle_dir), "rewritten": False, "error": str(exc)})

    base_url, finalize_results = _finalize_all_bundles(
        review_root=review_root,
        jar_path=jar_path,
        host=DEFAULT_REVIEW_HOST,
        port=int(args.review_port),
        reviewer=str(args.reviewer),
    )

    import_result = _run_import_boundary(
        review_root=review_root,
        output_root=pilot_root,
        import_mode=str(args.import_mode),
    )

    db_path = Path(import_result["db_path"])
    db_coverage = _query_db_coverage(db_path)
    approved_item_ids = _load_approved_item_ids(db_path, subject="math")

    runs: List[Dict[str, Any]] = []
    assembly_errors: List[Dict[str, Any]] = []
    try:
        runs = _run_assembly_preview_export_verify(
            pilot_root=pilot_root,
            db_path=db_path,
            item_ids=approved_item_ids,
            seed="coverage-expansion-v1",
        )
    except Exception as exc:  # noqa: BLE001
        assembly_errors.append({"code": "assembly_or_export_failed", "message": str(exc)})

    # Coverage gap analysis (very lightweight and honest).
    coverage_gaps: List[Dict[str, Any]] = []
    if db_coverage.get("approved_item_total", 0) == 0:
        coverage_gaps.append({"code": "no_approved_items", "message": "No approved_importable items were available; assembly/export could not run on approved items."})
    approved_subjects = {row.get("subject") for row in db_coverage.get("approved_items_by_subject", []) if isinstance(row, dict)}
    if approved_subjects and approved_subjects != {"math"}:
        pass
    elif approved_subjects == {"math"}:
        coverage_gaps.append({"code": "approved_subject_coverage_limited", "message": "Approved pool subject coverage is limited (only 'math' in this run)."})
    else:
        coverage_gaps.append({"code": "approved_subject_coverage_empty", "message": "No approved subjects were imported in this run."})

    if not db_coverage.get("approved_rubric_counts"):
        coverage_gaps.append({"code": "no_approved_rubrics", "message": "No rubric-bearing approved items were imported; teacher rubric rendering coverage is limited."})

    if assembly_errors:
        coverage_gaps.append({"code": "assembly_export_errors", "message": "One or more assembly/export steps failed; see errors list in the JSON report."})

    run_verdict_counts: Dict[str, Any] = {
        "export_verdicts": {},
        "acceptance_verdicts": {},
        "acceptance_issue_code_counts": {},
    }
    if runs:
        export_counts: Dict[str, int] = {}
        acceptance_counts: Dict[str, int] = {}
        issue_code_counts: Dict[str, int] = {}
        for run in runs:
            if not isinstance(run, dict):
                continue
            export_verdict = str(run.get("export_verdict", "") or "")
            if export_verdict:
                export_counts[export_verdict] = export_counts.get(export_verdict, 0) + 1
            acceptance_verdict = str(run.get("acceptance_verdict", "") or "")
            if acceptance_verdict:
                acceptance_counts[acceptance_verdict] = acceptance_counts.get(acceptance_verdict, 0) + 1
            if acceptance_verdict == "blocked":
                acc_path = Path(str(run.get("acceptance_report", "") or ""))
                if acc_path.is_file():
                    payload = _read_json(acc_path)
                    for issue in payload.get("issues", []) if isinstance(payload.get("issues"), list) else []:
                        if isinstance(issue, dict):
                            code = str(issue.get("code", "") or "")
                            if code:
                                issue_code_counts[code] = issue_code_counts.get(code, 0) + 1
        run_verdict_counts = {
            "export_verdicts": export_counts,
            "acceptance_verdicts": acceptance_counts,
            "acceptance_issue_code_counts": issue_code_counts,
        }
        if acceptance_counts.get("blocked", 0) > 0:
            coverage_gaps.append(
                {
                    "code": "docx_acceptance_blocked",
                    "message": "One or more assembled-exam DOCX exports failed acceptance verification; see acceptance_issue_code_counts.",
                    "details": {"acceptance_issue_code_counts": issue_code_counts},
                }
            )

    # Recommendation: conservative; expand based on what is actually covered.
    acceptance_verdicts = [str(run.get("acceptance_verdict", "")) for run in runs]
    export_verdicts = [str(run.get("export_verdict", "")) for run in runs]
    all_safe = bool(runs) and all(v == "safe_to_accept" for v in acceptance_verdicts) and all(v == "safe_to_export" for v in export_verdicts)
    if all_safe and not assembly_errors:
        verdict = "sufficient_for_limited_internal_use"
        message = "Exporter/verification are green on the approved pool available in this pilot; broader internal use still depends on expanding real approved_importable coverage."
    else:
        verdict = "not_sufficient_yet"
        message = "Pilot coverage did not reach a stable green run across the intended coverage set; expand approved pool and rerun."

    report: Dict[str, Any] = {
        "schema_version": "assembled_exam_coverage_expansion_pilot.v1",
        "artifact_type": "assembled_exam_coverage_expansion_pilot_report",
        "generated_at": _now_iso(),
        "pilot_root": str(pilot_root),
        "review_root": str(review_root),
        "review_server_url": base_url,
        "jar_path": str(jar_path),
        "inputs": {
            "real_contracts_root": str(args.real_contracts_root.resolve()),
            "fixture_cases_root": str(args.fixture_cases_root.resolve()),
            "fixture_cases": fixture_cases,
            "copied_real_bundle_dirs": [str(path) for path in copied_real],
            "copied_fixture_bundle_dirs": [str(path) for path in copied_fixture],
            "fixture_item_id_rewrites": fixture_rewrites,
        },
        "finalize": {
            "reviewer": str(args.reviewer),
            "bundle_count": len(finalize_results),
            "bundles": [result.as_dict() for result in finalize_results],
        },
        "import": import_result,
        "db_path": str(db_path),
        "db_coverage": db_coverage,
        "approved_item_ids_used_for_assembly": approved_item_ids,
        "runs": runs,
        "run_verdict_counts": run_verdict_counts,
        "errors": assembly_errors,
        "coverage_gaps": coverage_gaps,
        "recommendation": {"verdict": verdict, "message": message},
    }

    report_json = pilot_root / "assembled_exam_coverage_expansion_pilot_report.json"
    report_md = pilot_root / "assembled_exam_coverage_expansion_pilot_report.md"
    _write_text(report_json, _json(report) + "\n")
    _write_text(report_md, _render_pilot_report_md(report))
    print(_json(report))
    return 0 if not assembly_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
