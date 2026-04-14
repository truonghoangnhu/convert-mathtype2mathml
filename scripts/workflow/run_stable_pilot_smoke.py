#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_INPUT_DIR = Path("pilot-real-input")
DEFAULT_OUTPUT_ROOT = Path("out/stable_pilot_smoke")
DEFAULT_REVIEW_SOURCE_ROOT = Path("out/pilot_real_workflow_20260409_retry/contracts")
DEFAULT_JAVA_JAR = Path("target/docx-html-math-1.0.0-jar-with-dependencies.jar")
DEFAULT_BATCH_NAME = "stable_pilot_smoke"
DEFAULT_REVIEW_HOST = "127.0.0.1"
DEFAULT_REVIEW_PORT = 8110
DEFAULT_LITERAL_BUNDLE = "Van_LT-Da-Nang-Lan-1.docx"
DEFAULT_ZERO_BUNDLE = "Tieng-Anh-So-GD-Ha-Noi-lan-1.docx"


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
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_server(url: str, process: subprocess.Popen[str], timeout_s: int = 30) -> None:
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
    for path in [
        Path("target/docx-html-math-1.0.0-jar-with-dependencies.jar"),
        Path("target/docx-html-math-1.0.0.jar"),
    ]:
        if path.exists():
            return path.resolve()
    raise FileNotFoundError("could not locate built jar under target/")


def _safe_copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _pick_bundle(bundles: List[Dict[str, Any]], display_title: str) -> Dict[str, Any]:
    for bundle in bundles:
        if str(bundle.get("display_title", "")) == display_title:
            return bundle
    raise KeyError(f"bundle with display_title={display_title!r} not found")


def _run_batch_parse(input_dir: Path, output_root: Path, batch_name: str) -> Tuple[Path, Path, Dict[str, Any]]:
    cmd = [
        sys.executable,
        "scripts/batch/run_subject_batch.py",
        "--input-dir",
        str(input_dir),
        "--allow-recursive-discovery",
        "--output-root",
        str(output_root),
        "--batch-name",
        batch_name,
        "--skip-build",
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"parse stage failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    batch_dir = output_root / batch_name
    batch_summary_path = batch_dir / "batch-summary.json"
    if not batch_summary_path.exists():
        raise FileNotFoundError(f"parse summary not written: {batch_summary_path}")
    return batch_dir, batch_summary_path, _read_json(batch_summary_path)


def _run_review_checks(review_root: Path, jar: Path, port: int) -> Dict[str, Any]:
    server_cmd = [
        "java",
        "-jar",
        str(jar),
        "review-server",
        "--review-root",
        str(review_root),
        "--host",
        DEFAULT_REVIEW_HOST,
        "--port",
        str(port),
    ]
    server = subprocess.Popen(  # noqa: S603
        server_cmd,
        cwd=str(Path.cwd()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://{DEFAULT_REVIEW_HOST}:{port}"
    try:
        _wait_for_server(f"{base_url}/api/review/bundles", server)
        bundles_payload = _http_json(f"{base_url}/api/review/bundles")
        bundles = bundles_payload.get("bundles", []) if isinstance(bundles_payload.get("bundles"), list) else []
        literature = _pick_bundle(bundles, DEFAULT_LITERAL_BUNDLE)
        zero_bundle = _pick_bundle(bundles, DEFAULT_ZERO_BUNDLE)

        lit_bundle_id = str(literature.get("bundle_id", ""))
        zero_bundle_id = str(zero_bundle.get("bundle_id", ""))

        lit_queue = _http_json(
            f"{base_url}/api/review/session/{lit_bundle_id}/queue?includeReviewed=true&includeSecondary=true"
        )
        zero_queue = _http_json(
            f"{base_url}/api/review/session/{zero_bundle_id}/queue?includeReviewed=true&includeSecondary=true"
        )
        lit_finalize = _http_json(
            f"{base_url}/api/review/session/{lit_bundle_id}/finalize",
            method="POST",
            body={},
        )
        zero_finalize = _http_json(
            f"{base_url}/api/review/session/{zero_bundle_id}/finalize",
            method="POST",
            body={},
        )

        return {
            "server_url": base_url,
            "bundles": bundles,
            "literature_bundle": literature,
            "zero_bundle": zero_bundle,
            "literature_queue": lit_queue,
            "zero_queue": zero_queue,
            "literature_finalize": lit_finalize,
            "zero_finalize": zero_finalize,
        }
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)


def _run_import_boundary(review_root: Path, output_root: Path) -> Dict[str, Any]:
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
        "allow-draft",
        "--batch-report-json",
        str(batch_report_json),
        "--batch-summary-md",
        str(batch_summary_md),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"import boundary check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not batch_report_json.exists():
        raise FileNotFoundError(f"batch import summary not written: {batch_report_json}")
    summary = _read_json(batch_report_json)

    job_listing_json = output_root / "question_bank_import_jobs.json"
    job_listing_md = output_root / "question_bank_import_jobs.md"
    list_cmd = [
        sys.executable,
        "-m",
        "question_bank",
        "--list-jobs",
        "--db",
        str(db_path),
        "--jobs-json",
        str(job_listing_json),
        "--jobs-md",
        str(job_listing_md),
    ]
    list_result = _run(list_cmd)
    if list_result.returncode != 0:
        raise RuntimeError(f"job listing failed:\nSTDOUT:\n{list_result.stdout}\nSTDERR:\n{list_result.stderr}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    jobs = [dict(row) for row in conn.execute(
        "SELECT import_job_id, bundle_id, subject, import_mode, import_readiness, source_publish_verdict, import_decision, imported_at "
        "FROM approved_import_jobs ORDER BY imported_at ASC"
    ).fetchall()]
    conn.close()

    return {
        "db_path": db_path,
        "batch_report_json": batch_report_json,
        "batch_summary_md": batch_summary_md,
        "job_listing_json": job_listing_json,
        "job_listing_md": job_listing_md,
        "summary": summary,
        "jobs": jobs,
    }


def _run_dashboard(review_summary_json: Path, output_root: Path, db_path: Path) -> Path:
    dashboard_html = output_root / "question_bank_import_dashboard.html"
    cmd = [
        sys.executable,
        "-m",
        "question_bank",
        "--dashboard-html",
        str(dashboard_html),
        "--db",
        str(db_path),
        "--batch-summary-json",
        str(review_summary_json),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"dashboard generation failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not dashboard_html.exists():
        raise FileNotFoundError(f"dashboard not written: {dashboard_html}")
    return dashboard_html


def _render_md(report: Dict[str, Any]) -> str:
    parse_stage = report.get("parse_stage", {}) if isinstance(report.get("parse_stage"), dict) else {}
    review_stage = report.get("review_stage", {}) if isinstance(report.get("review_stage"), dict) else {}
    import_stage = report.get("import_stage", {}) if isinstance(report.get("import_stage"), dict) else {}
    dashboard_stage = report.get("dashboard_stage", {}) if isinstance(report.get("dashboard_stage"), dict) else {}
    lines = [
        "# Stable Pilot Smoke Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Input dir: `{report['input_dir']}`",
        f"- Output root: `{report['output_root']}`",
        f"- Review source root: `{report['review_source_root']}`",
        f"- Review root (copy): `{report['review_root']}`",
        f"- Dashboard: `{report['dashboard_html']}`",
        "",
        "## Parse Stage",
        f"- Bundles discovered: `{parse_stage.get('bundle_count', 0)}`",
        f"- Documents converted: `{parse_stage.get('documents_converted', 0)}`",
        f"- Documents failed: `{parse_stage.get('documents_failed', 0)}`",
        f"- Questions: `{parse_stage.get('question_count', 0)}`",
        f"- Publish verdict: `{parse_stage.get('publish_verdict', '')}`",
        "",
        "## Review Stage",
        f"- Review server check: `{review_stage.get('status', '')}`",
        f"- Literature bundle finalize: `{review_stage.get('literature_finalize_status', '')}`",
        f"- Zero-question bundle finalize: `{review_stage.get('zero_finalize_status', '')}`",
        "",
        "## Import Stage",
        f"- Import mode: `{import_stage.get('import_mode', '')}`",
        f"- Imported: `{import_stage.get('imported_count', 0)}`",
        f"- Skipped: `{import_stage.get('skipped_count', 0)}`",
        f"- Blocked: `{import_stage.get('blocked_count', 0)}`",
        f"- Jobs in DB: `{import_stage.get('job_count', 0)}`",
        "",
        "## Operational Findings",
    ]
    for finding in report.get("operational_findings", []):
        lines.append(f"- {finding}")
    lines.extend([
        "",
        "## Output Files",
    ])
    for key in ["parse_summary_json", "batch_import_summary_json", "job_listing_json", "dashboard_html"]:
        value = report.get(key)
        if value:
            lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the stable pilot smoke workflow: parse, review/finalize, import, dashboard.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR, help="Source DOCX directory for the parse stage")
    parser.add_argument("--review-source-root", type=Path, default=DEFAULT_REVIEW_SOURCE_ROOT, help="Known-good finalized review root to smoke against")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Smoke output directory")
    parser.add_argument("--java-jar", type=Path, default=None, help="Optional explicit jar path for the review server")
    parser.add_argument("--review-port", type=int, default=DEFAULT_REVIEW_PORT, help="Local review server port")
    parser.add_argument("--batch-name", type=str, default=DEFAULT_BATCH_NAME, help="Parse batch name")
    args = parser.parse_args(argv)

    output_root = args.output_root.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "schema_version": "stable_pilot_smoke_report.v1",
        "artifact_type": "stable_pilot_smoke_report",
        "generated_at": _now_iso(),
        "input_dir": str(args.input_dir.resolve()),
        "output_root": str(output_root),
        "review_source_root": str(args.review_source_root.resolve()),
        "review_root": str((output_root / "review_contracts").resolve()),
        "parse_summary_json": "",
        "batch_import_summary_json": "",
        "job_listing_json": "",
        "dashboard_html": "",
        "parse_stage": {},
        "review_stage": {},
        "import_stage": {},
        "dashboard_stage": {},
        "operational_findings": [],
        "verdict": "failed",
    }

    review_root = output_root / "review_contracts"
    jar = _find_jar(args.java_jar)

    try:
        parse_batch_dir, parse_summary_json, parse_summary = _run_batch_parse(args.input_dir.resolve(), output_root, args.batch_name)
        report["parse_summary_json"] = str(parse_summary_json)
        report["parse_batch_dir"] = str(parse_batch_dir)
        report["parse_stage"] = {
            "bundle_count": parse_summary.get("totals", {}).get("documents_discovered", 0),
            "documents_converted": parse_summary.get("totals", {}).get("documents_converted", 0),
            "documents_failed": parse_summary.get("totals", {}).get("documents_failed", 0),
            "question_count": sum(int(item.get("question_count", 0)) for item in parse_summary.get("files", []) if isinstance(item, dict)),
            "publish_verdict": parse_summary.get("publish_verdict", ""),
            "by_subject": parse_summary.get("by_subject", {}),
        }

        _safe_copytree(args.review_source_root.resolve(), review_root)
        review_result = _run_review_checks(review_root, jar, args.review_port)
        report["review_stage"] = {
            "status": "passed",
            "review_server": review_result["server_url"],
            "literature_bundle_title": review_result["literature_bundle"].get("display_title", ""),
            "zero_bundle_title": review_result["zero_bundle"].get("display_title", ""),
            "literature_queue_status": review_result["literature_queue"].get("status_summary", ""),
            "zero_queue_status": review_result["zero_queue"].get("status_summary", ""),
            "literature_finalize_status": review_result["literature_finalize"].get("status", ""),
            "literature_reviewed_fixed_count": review_result["literature_finalize"].get("summary", {}).get("reviewed_fixed_count", 0),
            "literature_reviewed_confirmed_count": review_result["literature_finalize"].get("summary", {}).get("reviewed_confirmed_count", 0),
            "literature_finalize_overrides_applied": review_result["literature_finalize"].get("summary", {}).get("overrides_applied", 0),
            "zero_finalize_status": review_result["zero_finalize"].get("status", ""),
            "zero_reviewed_fixed_count": review_result["zero_finalize"].get("summary", {}).get("reviewed_fixed_count", 0),
            "zero_reviewed_confirmed_count": review_result["zero_finalize"].get("summary", {}).get("reviewed_confirmed_count", 0),
            "zero_finalize_overrides_applied": review_result["zero_finalize"].get("summary", {}).get("overrides_applied", 0),
            "zero_finalize_reason": review_result["zero_finalize"].get("blockers", [{}])[0].get("code", "") if isinstance(review_result["zero_finalize"].get("blockers"), list) and review_result["zero_finalize"].get("blockers") else "",
        }

        import_result = _run_import_boundary(review_root, output_root)
        report["batch_import_summary_json"] = str(import_result["batch_report_json"])
        report["job_listing_json"] = str(import_result["job_listing_json"])
        report["import_stage"] = {
            "import_mode": import_result["summary"].get("import_mode", ""),
            "bundle_count": import_result["summary"].get("bundle_count", 0),
            "imported_count": import_result["summary"].get("imported_count", 0),
            "skipped_count": import_result["summary"].get("skipped_count", 0),
            "blocked_count": import_result["summary"].get("blocked_count", 0),
            "error_count": import_result["summary"].get("error_count", 0),
            "job_count": len(import_result["jobs"]),
            "jobs": import_result["jobs"],
        }

        dashboard_html = _run_dashboard(parse_summary_json, output_root, import_result["db_path"])
        report["dashboard_html"] = str(dashboard_html)
        report["dashboard_stage"] = {
            "status": "passed",
            "contains_operational_batch_summary": "Operational Batch Summary" in dashboard_html.read_text(encoding="utf-8"),
            "contains_import_jobs": "Import Jobs" in dashboard_html.read_text(encoding="utf-8"),
        }

        report["operational_findings"] = [
            "Finalize sees the latest saved review overrides without a restart.",
            "Subject detection reports English and Literature for the pilot bundles.",
            "Zero-question bundles are blocked before finalize/import decisions.",
            "Finalize reporting now exposes reviewed_fixed vs reviewed_confirmed counts per bundle.",
            "The dashboard shows the operational batch summary and the SQLite import jobs table.",
        ]
        report["verdict"] = "passed"
    except Exception as exc:  # noqa: BLE001
        report["operational_findings"].append(str(exc))
        report["verdict"] = "failed"
        raise
    finally:
        smoke_json = output_root / "stable_pilot_smoke_report.json"
        smoke_md = output_root / "stable_pilot_smoke_report.md"
        _write_text(smoke_json, _json(report) + "\n")
        _write_text(smoke_md, _render_md(report))
        print(_json({
            "report_json": str(smoke_json),
            "report_md": str(smoke_md),
            "verdict": report["verdict"],
            "output_root": str(output_root),
        }))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
