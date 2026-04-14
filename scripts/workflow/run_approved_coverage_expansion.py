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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_REAL_CONTRACTS_ROOT = Path("out/full-corpus-in-test-validation-20260409-095900")
DEFAULT_OUTPUT_PARENT = Path("out")
DEFAULT_PREFIX = "approved-coverage-expansion"

DEFAULT_REVIEW_HOST = "127.0.0.1"
DEFAULT_REVIEW_PORT = 8122
DEFAULT_REVIEWER = "approved_coverage_bot"

DEFAULT_BASELINE_DB = Path("out/coverage-expansion-pilot-20260410-023545/question_bank_import.sqlite")


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


def _blocked_items_with_answer_summary(bundle_dir: Path) -> Dict[str, Any]:
    qb = _read_json(bundle_dir / "question_bank_items.json")
    exam = _read_json(bundle_dir / "exam_bundle.json")

    ans_map: Dict[int, Dict[str, Any]] = {}
    for entry in (exam.get("answer_summary") or {}).get("entries") or []:
        if not isinstance(entry, dict):
            continue
        qn = str(entry.get("question_number", "") or "")
        if qn.isdigit():
            ans_map[int(qn)] = entry

    blocked: List[Dict[str, Any]] = []
    fixable: List[Dict[str, Any]] = []
    for item in qb.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        ak = item.get("answer_key") or {}
        rec = item.get("reconciliation") or {}
        mode = str((ak.get("mode") or "")).strip()
        status = str((rec.get("status") or "")).strip()
        if mode != "none" and status != "blocked":
            continue
        qn = int(item.get("question_number") or 0)
        entry = ans_map.get(qn)
        record = {
            "question_number": qn,
            "item_id": str(item.get("item_id", "") or ""),
            "question_type": str(item.get("question_type", "") or ""),
            "reconciliation_status": status,
            "answer_mode": mode,
            "answer_summary_entry": entry or None,
        }
        blocked.append(record)
        if entry and str(entry.get("mode") or "") in {"single_choice", "short_answer", "boolean_group"} and str(entry.get("value") or "").strip():
            fixable.append(record)

    return {
        "bundle_dir": str(bundle_dir),
        "bundle_id": str(qb.get("bundle_id") or ""),
        "subject": str(qb.get("subject") or ""),
        "item_count": int(qb.get("item_count") or len(qb.get("items") or [])),
        "blocked_count": len(blocked),
        "blocked_fixable_via_answer_summary_count": len(fixable),
        "blocked_items": blocked,
        "fixable_items": fixable,
        "answer_summary_entry_count": len(ans_map),
    }


def _apply_answer_summary_override(
    *,
    base_url: str,
    bundle_id: str,
    item_id: str,
    question_number: int,
    entry: Dict[str, Any],
    reviewer: str,
) -> Dict[str, Any]:
    mode = str(entry.get("mode") or "").strip()
    value = entry.get("value")
    edits: Dict[str, Any] = {}
    if mode == "single_choice":
        edits["answer_key"] = {"mode": "single_choice", "value": str(value).strip()}
    elif mode == "short_answer":
        edits["answer_key"] = {"mode": "short_answer", "value": str(value).strip()}
    elif mode == "boolean_group":
        # Prefer explicit structured dict if present; otherwise leave unresolved (no guessing).
        if isinstance(value, dict):
            edits["boolean_subanswers"] = value
        else:
            raise ValueError(f"boolean_group answer_summary value is not a dict for q{question_number}: {value!r}")
    else:
        raise ValueError(f"unsupported answer_summary mode for override: {mode!r}")

    body = {
        "review_status": "reviewed_fixed",
        "review_note": f"Applied explicit answer_summary entry for question_number={question_number}",
        "reviewed_by": reviewer,
        "reviewer": reviewer,
        "edits": edits,
    }
    return _http_json(f"{base_url}/api/review/session/{bundle_id}/question/{item_id}/save", method="POST", body=body)


def _finalize_bundle(*, base_url: str, bundle_id: str, finalizer: str, note: str) -> Dict[str, Any]:
    body = {"finalized_by": finalizer, "finalize_note": note}
    return _http_json(f"{base_url}/api/review/session/{bundle_id}/finalize", method="POST", body=body)


def _run_batch_import(*, batch_root: Path, db_path: Path, output_root: Path, mode: str) -> Dict[str, Any]:
    out_json = output_root / "question_bank_batch_import_summary.json"
    out_md = output_root / "question_bank_batch_import_summary.md"
    cmd = [
        sys.executable,
        "-m",
        "question_bank",
        "--batch-root",
        str(batch_root),
        "--db",
        str(db_path),
        "--mode",
        mode,
        "--batch-report-json",
        str(out_json),
        "--batch-summary-md",
        str(out_md),
    ]
    completed = _run(cmd)
    return {
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "batch_summary_json": str(out_json),
        "batch_summary_md": str(out_md),
    }


def _query_db_coverage(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"db_path": str(db_path), "exists": False}
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
            "db_path": str(db_path),
            "exists": True,
            "subject_readiness_counts": subject_readiness,
            "approved_item_total": int(approved_total),
            "approved_items_by_subject": approved_by_subject,
            "approved_rubric_counts": approved_rubric,
        }
    finally:
        conn.close()


def _render_report_md(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Approved Coverage Expansion Report")
    lines.append("")
    lines.append(f"- created_at: `{report.get('created_at','')}`")
    lines.append(f"- real_contracts_root: `{report.get('real_contracts_root','')}`")
    lines.append(f"- output_root: `{report.get('output_root','')}`")
    lines.append("")

    lines.append("## Candidate Scan")
    scan = report.get("scan", []) if isinstance(report.get("scan"), list) else []
    lines.append("| bundle | subject | item_count | blocked | fixable_via_answer_summary | selected |")
    lines.append("| --- | --- | ---: | ---: | ---: | --- |")
    selected = set(report.get("selected_bundle_names", []) or [])
    for row in scan:
        if not isinstance(row, dict):
            continue
        name = Path(str(row.get("bundle_dir", "") or "")).name
        lines.append(
            "| {name} | {subject} | {item_count} | {blocked} | {fixable} | {sel} |".format(
                name=name,
                subject=str(row.get("subject", "")),
                item_count=int(row.get("item_count", 0) or 0),
                blocked=int(row.get("blocked_count", 0) or 0),
                fixable=int(row.get("blocked_fixable_via_answer_summary_count", 0) or 0),
                sel="yes" if name in selected else "",
            )
        )
    lines.append("")

    lines.append("## Coverage Growth")
    before = report.get("coverage_before", {}) if isinstance(report.get("coverage_before"), dict) else {}
    after = report.get("coverage_after", {}) if isinstance(report.get("coverage_after"), dict) else {}
    lines.append(f"- baseline_db: `{report.get('baseline_db_path','')}`")
    lines.append(f"- before approved_item_total: `{before.get('approved_item_total','')}`")
    lines.append(f"- after approved_item_total: `{after.get('approved_item_total','')}`")
    lines.append(f"- after approved_items_by_subject: `{after.get('approved_items_by_subject','')}`")
    lines.append(f"- after approved_rubric_counts: `{after.get('approved_rubric_counts','')}`")
    lines.append("")

    rec = report.get("recommendation", {}) if isinstance(report.get("recommendation"), dict) else {}
    lines.append("## Recommendation")
    lines.append(f"- verdict: `{rec.get('verdict','')}`")
    if rec.get("message"):
        lines.append(f"- note: {rec.get('message')}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@dataclass
class ExpansionResult:
    selected_bundle_names: List[str]
    overrides_applied: List[Dict[str, Any]]
    finalize_results: List[Dict[str, Any]]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Expand approved_importable coverage using existing frozen review/finalize/import flow (no parser changes).")
    parser.add_argument("--real-contracts-root", type=Path, default=DEFAULT_REAL_CONTRACTS_ROOT, help="Root containing bundle contract dirs")
    parser.add_argument("--output-parent", type=Path, default=DEFAULT_OUTPUT_PARENT, help="Output parent directory")
    parser.add_argument("--baseline-db", type=Path, default=DEFAULT_BASELINE_DB, help="Baseline SQLite DB for before/after comparison")
    parser.add_argument("--jar", type=Path, default=None, help="Path to the built converter jar (for review-server)")
    parser.add_argument("--review-port", type=int, default=DEFAULT_REVIEW_PORT, help="Review server port")
    parser.add_argument("--reviewer", type=str, default=DEFAULT_REVIEWER, help="Reviewer identity recorded in review artifacts")
    parser.add_argument("--max-bundles", type=int, default=3, help="Maximum bundles to attempt approving in this pass")
    args = parser.parse_args(argv)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_root = (args.output_parent / f"{DEFAULT_PREFIX}-{ts}").resolve()
    review_root = (output_root / "review_root").resolve()
    db_path = (output_root / "question_bank_import.sqlite").resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    review_root.mkdir(parents=True, exist_ok=True)

    jar_path = _find_jar(args.jar)

    scan: List[Dict[str, Any]] = []
    candidates: List[Tuple[int, str, Path, Dict[str, Any]]] = []
    for bundle_dir in _discover_bundle_dirs(args.real_contracts_root.resolve()):
        row = _blocked_items_with_answer_summary(bundle_dir)
        scan.append(row)
        blocked = int(row.get("blocked_count", 0) or 0)
        fixable = int(row.get("blocked_fixable_via_answer_summary_count", 0) or 0)
        subject = str(row.get("subject") or "")
        # Select only bundles where every blocked item has an explicit answer_summary entry (no guessing).
        if blocked > 0 and blocked == fixable:
            # Prefer non-math first, then smaller fix scope.
            score = blocked + (0 if subject != "math" else 1000)
            candidates.append((score, bundle_dir.name, bundle_dir, row))

    candidates.sort(key=lambda t: (t[0], t[1]))
    selected = candidates[: max(0, int(args.max_bundles))]

    copied = [_copy_bundle_dir(src, review_root) for _, _, src, _ in selected]
    selected_bundle_names = [p.name for p in copied]

    # Start review-server over the isolated review_root.
    server_cmd = [
        "java",
        "-jar",
        str(jar_path),
        "review-server",
        "--review-root",
        str(review_root),
        "--host",
        DEFAULT_REVIEW_HOST,
        "--port",
        str(int(args.review_port)),
    ]
    server = subprocess.Popen(  # noqa: S603
        server_cmd,
        cwd=str(Path.cwd()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://{DEFAULT_REVIEW_HOST}:{int(args.review_port)}"
    try:
        _wait_for_server(f"{base_url}/api/review/bundles", server, timeout_s=60)

        bundle_index = _http_json(f"{base_url}/api/review/bundles").get("bundles", [])
        summary_by_name: Dict[str, Dict[str, Any]] = {}
        for b in bundle_index:
            if not isinstance(b, dict):
                continue
            bundle_path = str(b.get("bundle_path", "") or "")
            name = Path(bundle_path).name if bundle_path else str(b.get("bundle_id", "") or "")
            if name:
                summary_by_name[name] = b

        overrides_applied: List[Dict[str, Any]] = []
        finalize_results: List[Dict[str, Any]] = []

        # Apply only explicit answer_summary -> answer_key overrides for blocked items.
        for _, _, _, meta in selected:
            bundle_name = Path(str(meta.get("bundle_dir", "") or "")).name
            bundle_id = str(meta.get("bundle_id") or "") or bundle_name
            bundle_summary = summary_by_name.get(bundle_name, {})
            required_pending = int(bundle_summary.get("review_item_count", -1) or -1)
            conflict_count = int(bundle_summary.get("conflict_count", 0) or 0)
            blocked_count = int(meta.get("blocked_count", 0) or 0)

            # Guard: only attempt to approve bundles where the required review set matches the blocked set
            # we can explicitly repair via answer_summary overrides, and where there are no conflicts.
            if required_pending >= 0 and required_pending != blocked_count:
                finalize_results.append(
                    {
                        "bundle": bundle_name,
                        "bundle_id": bundle_id,
                        "allowed": False,
                        "status": "skipped",
                        "reason": f"required_pending_count={required_pending} does not match blocked_count={blocked_count}",
                        "bundle_summary": bundle_summary,
                    }
                )
                continue
            if conflict_count > 0:
                finalize_results.append(
                    {
                        "bundle": bundle_name,
                        "bundle_id": bundle_id,
                        "allowed": False,
                        "status": "skipped",
                        "reason": f"bundle has conflict_count={conflict_count}; not auto-approving",
                        "bundle_summary": bundle_summary,
                    }
                )
                continue

            for item in meta.get("fixable_items", []) or []:
                if not isinstance(item, dict):
                    continue
                entry = item.get("answer_summary_entry")
                if not isinstance(entry, dict):
                    continue
                try:
                    resp = _apply_answer_summary_override(
                        base_url=base_url,
                        bundle_id=bundle_id,
                        item_id=str(item.get("item_id") or ""),
                        question_number=int(item.get("question_number") or 0),
                        entry=entry,
                        reviewer=str(args.reviewer),
                    )
                    overrides_applied.append(
                        {
                            "bundle": bundle_name,
                            "bundle_id": bundle_id,
                            "item_id": str(item.get("item_id") or ""),
                            "question_number": int(item.get("question_number") or 0),
                            "answer_summary_mode": str(entry.get("mode") or ""),
                            "answer_summary_value": entry.get("value"),
                            "save_status": resp.get("saved_override", {}).get("status"),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    overrides_applied.append(
                        {
                            "bundle": bundle_name,
                            "bundle_id": bundle_id,
                            "item_id": str(item.get("item_id") or ""),
                            "question_number": int(item.get("question_number") or 0),
                            "error": str(exc),
                        }
                    )

            # Finalize bundle (will block if any required items remain pending).
            try:
                fin = _finalize_bundle(
                    base_url=base_url,
                    bundle_id=bundle_id,
                    finalizer=str(args.reviewer),
                    note="approved-coverage-expansion: applied explicit answer_summary overrides where parser was blocked",
                )
                finalize_results.append({"bundle": bundle_name, "bundle_id": bundle_id, **fin})
            except Exception as exc:  # noqa: BLE001
                finalize_results.append({"bundle": bundle_name, "bundle_id": bundle_id, "allowed": False, "status": "blocked", "error": str(exc)})

    finally:
        try:
            server.terminate()
        except Exception:  # noqa: BLE001
            pass
        try:
            server.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                server.kill()
            except Exception:  # noqa: BLE001
                pass

    import_result = _run_batch_import(batch_root=review_root, db_path=db_path, output_root=output_root, mode="approved-only")
    coverage_before = _query_db_coverage(args.baseline_db.resolve())
    coverage_after = _query_db_coverage(db_path)

    rec_verdict = "still_needs_more_approved_coverage"
    msg = "Approved pool expanded, but further subject breadth (physics/chemistry) and real rubric-bearing coverage are still needed."
    if int(coverage_after.get("approved_item_total", 0) or 0) >= int((coverage_before.get("approved_item_total", 0) or 0) + 50):
        rec_verdict = "sufficient_for_broader_internal_use"
        msg = "Approved pool growth is substantial; proceed with broader internal use while continuing to expand coverage."

    report: Dict[str, Any] = {
        "schema_version": "approved_coverage_expansion_report.v1",
        "created_at": _now_iso(),
        "real_contracts_root": str(args.real_contracts_root.resolve()),
        "output_root": str(output_root),
        "review_root": str(review_root),
        "jar_path": str(jar_path),
        "baseline_db_path": str(args.baseline_db.resolve()),
        "scan": scan,
        "selected_bundle_names": selected_bundle_names,
        "overrides_applied": overrides_applied,
        "finalize_results": finalize_results,
        "import_result": import_result,
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "recommendation": {"verdict": rec_verdict, "message": msg},
    }

    out_json = output_root / "approved_coverage_expansion_report.json"
    out_md = output_root / "approved_coverage_expansion_report.md"
    _write_text(out_json, _json(report) + "\n")
    _write_text(out_md, _render_report_md(report))

    print(_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
