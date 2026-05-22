#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.batch.run_subject_batch import default_project_jar, latest_source_mtime_ns, safe_artifact_part


def _run_command(cmd: List[str], cwd: Path, log_path: Path, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    combined = (result.stdout or "") + ("\n" if result.stdout and result.stderr else "") + (result.stderr or "")
    log_path.write_text(combined, encoding="utf-8")
    return result


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _discover_inputs(input_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in sorted(input_dir.glob("*.docx")):
        if path.is_file() and not path.name.startswith("~$"):
            files.append(path.resolve())
    return files


def _default_jobs(file_count: int) -> int:
    if file_count <= 1:
        return 1
    cpu_count = os.cpu_count() or 2
    return max(1, min(4, cpu_count, file_count))


def _build_if_needed(*, project_jar: Path, force_build: bool, skip_build: bool, output_dir: Path) -> Dict[str, Any]:
    build_log = output_dir / "logs" / "build.log"
    if skip_build:
        build_log.parent.mkdir(parents=True, exist_ok=True)
        build_log.write_text("Build skipped by --skip-build.\n", encoding="utf-8")
        return {"build_executed": False, "build_log": str(build_log.resolve())}

    need_build = force_build or not project_jar.exists()
    if not need_build and project_jar.stat().st_mtime_ns < latest_source_mtime_ns(ROOT):
        need_build = True

    if not need_build:
        build_log.parent.mkdir(parents=True, exist_ok=True)
        build_log.write_text("Build skipped: output jar newer than source tree.\n", encoding="utf-8")
        return {"build_executed": False, "build_log": str(build_log.resolve())}

    started = time.perf_counter()
    result = _run_command(["mvn", "-q", "-DskipTests", "package"], ROOT, build_log)
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"Build failed with exit code {result.returncode}. See {build_log}")
    return {"build_executed": True, "build_log": str(build_log.resolve()), "build_seconds": elapsed}


def _run_one(
    *,
    docx_path: Path,
    input_dir: Path,
    output_dir: Path,
    project_jar: Path,
    output_mode: str,
    subject: Optional[str],
) -> Dict[str, Any]:
    safe_stem = safe_artifact_part(docx_path.stem)
    log_path = output_dir / "logs" / f"{safe_stem}.run_subject_batch.log"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/batch/run_subject_batch.py"),
        "--input-docx",
        str(docx_path),
        "--input-dir",
        str(input_dir),
        "--output-root",
        str(output_dir),
        "--batch-name",
        safe_stem,
        "--project-jar",
        str(project_jar),
        "--output-mode",
        output_mode,
        "--skip-build",
    ]
    if subject:
        cmd.extend(["--subject", subject])

    started = time.perf_counter()
    result = _run_command(cmd, ROOT, log_path)
    elapsed = time.perf_counter() - started

    batch_dir = output_dir / safe_stem
    summary_path = batch_dir / "batch-summary.json"
    item: Dict[str, Any] = {
        "filename": docx_path.name,
        "path": str(docx_path.resolve()),
        "status": "error" if result.returncode else "ok",
        "seconds": elapsed,
        "batch_dir": str(batch_dir.resolve()),
        "batch_summary_json": str(summary_path.resolve()),
        "log": str(log_path.resolve()),
    }
    if result.returncode != 0:
        item["error"] = f"run_subject_batch failed with exit code {result.returncode}"
        return item
    if not summary_path.exists():
        item["status"] = "error"
        item["error"] = "batch-summary.json was not written"
        return item

    try:
        summary = _read_json(summary_path)
    except Exception as exc:
        item["status"] = "error"
        item["error"] = f"unable to read batch summary: {exc}"
        return item

    files = summary.get("files") if isinstance(summary.get("files"), list) else []
    first = files[0] if files else {}
    item.update(
        {
            "publish_verdict": summary.get("publish_verdict", ""),
            "subject": first.get("subject", summary.get("by_subject", {})),
            "html": first.get("html", ""),
            "qa_json": first.get("qa_json", ""),
            "contract_manifest": first.get("contract_manifest", ""),
            "question_count": first.get("question_count", 0),
            "reused": bool(first.get("reused", False)),
            "performance": summary.get("performance", {}),
            "totals": summary.get("totals", {}),
        }
    )
    if summary.get("publish_verdict") == "blocked" or int(summary.get("totals", {}).get("documents_failed", 0) or 0):
        item["status"] = "error"
        item["error"] = "batch completed but publish verdict is blocked"
    return item


def _render_markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Dotest Batch Summary",
        "",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Input dir: `{summary['input_dir']}`",
        f"- Output dir: `{summary['output_dir']}`",
        f"- Jobs: `{summary['jobs']}`",
        f"- Build executed: `{summary['build'].get('build_executed', False)}`",
        f"- Total seconds: `{summary['total_seconds']:.3f}`",
        "",
        "## Totals",
        "",
        f"- Files discovered: {summary['totals']['files_discovered']}",
        f"- Files ok: {summary['totals']['files_ok']}",
        f"- Files failed: {summary['totals']['files_failed']}",
        f"- Documents converted: {summary['totals']['documents_converted']}",
        f"- Documents failed: {summary['totals']['documents_failed']}",
        f"- MathML formulas: {summary['totals']['mathml_formulas']}",
        "",
        "## Files",
        "",
        "| file | status | seconds | subject | verdict | questions | html | contract |",
        "|---|---|---:|---|---|---:|---|---|",
    ]
    for item in summary["files"]:
        lines.append(
            "| `{}` | `{}` | {:.3f} | `{}` | `{}` | {} | `{}` | `{}` |".format(
                item.get("filename", ""),
                item.get("status", ""),
                float(item.get("seconds", 0.0) or 0.0),
                item.get("subject", ""),
                item.get("publish_verdict", ""),
                item.get("question_count", 0),
                item.get("html", ""),
                item.get("contract_manifest", ""),
            )
        )
    failures = [item for item in summary["files"] if item.get("status") != "ok"]
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"- `{item.get('filename', '')}`: {item.get('error', '')}; log `{item.get('log', '')}`")
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DOCX batch pipeline for top-level in/dotest/*.docx files in parallel.")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "in/dotest")
    parser.add_argument("--output-dir", type=Path, default=None, help="Default: <input-dir>/output-<timestamp>")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel file jobs. Default: min(4, CPU count, file count).")
    parser.add_argument("--project-jar", type=Path, default=None)
    parser.add_argument("--subject", choices=["generic", "physics", "chemistry", "math", "biology", "english", "literature"], default=None)
    parser.add_argument("--output-mode", choices=["internal", "publish"], default="publish")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--force-build", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    run_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = (args.output_dir.resolve() if args.output_dir else input_dir / f"output-{run_ts}").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = _discover_inputs(input_dir)
    if not files:
        raise SystemExit(f"No top-level .docx files found in {input_dir}")

    jobs = args.jobs if args.jobs and args.jobs > 0 else _default_jobs(len(files))
    jobs = max(1, min(jobs, len(files)))
    project_jar = args.project_jar.resolve() if args.project_jar else default_project_jar(ROOT)

    started = time.perf_counter()
    try:
        build_info = _build_if_needed(
            project_jar=project_jar,
            force_build=args.force_build,
            skip_build=args.skip_build,
            output_dir=output_dir,
        )
    except RuntimeError as exc:
        summary = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "jobs": jobs,
            "build": {"build_executed": True, "error": str(exc)},
            "total_seconds": time.perf_counter() - started,
            "totals": {
                "files_discovered": len(files),
                "files_ok": 0,
                "files_failed": len(files),
                "documents_converted": 0,
                "documents_failed": len(files),
                "mathml_formulas": 0,
            },
            "files": [
                {
                    "filename": path.name,
                    "path": str(path),
                    "status": "error",
                    "error": str(exc),
                    "seconds": 0.0,
                }
                for path in files
            ],
        }
        (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / "run_summary.md").write_text(_render_markdown(summary), encoding="utf-8")
        print(output_dir)
        return 1

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_path = {
            executor.submit(
                _run_one,
                docx_path=path,
                input_dir=input_dir,
                output_dir=output_dir,
                project_jar=project_jar,
                output_mode=args.output_mode,
                subject=args.subject,
            ): path
            for path in files
        }
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    {
                        "filename": path.name,
                        "path": str(path),
                        "status": "error",
                        "error": str(exc),
                        "seconds": 0.0,
                    }
                )

    results.sort(key=lambda item: item.get("filename", ""))
    totals = {
        "files_discovered": len(files),
        "files_ok": sum(1 for item in results if item.get("status") == "ok"),
        "files_failed": sum(1 for item in results if item.get("status") != "ok"),
        "documents_converted": sum(int(item.get("totals", {}).get("documents_converted", 0) or 0) for item in results),
        "documents_failed": sum(int(item.get("totals", {}).get("documents_failed", 0) or 0) for item in results),
        "mathml_formulas": sum(int(item.get("totals", {}).get("mathml_formulas", 0) or 0) for item in results),
    }
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "jobs": jobs,
        "project_jar": str(project_jar),
        "build": build_info,
        "total_seconds": time.perf_counter() - started,
        "totals": totals,
        "files": results,
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "run_summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    print(output_dir)
    return 1 if totals["files_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
