#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List


TYPE_KEYS = (
    "Equation.DSMT4",
    "Visio.Drawing.15",
    "ChemDraw.Document.6.0",
    "ChemDraw_x64.Document.6.0",
    ".emf",
    ".wmf",
)


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def discover_docx_inputs(
    input_dir: Path, output_root: Path, repo_root_path: Path
) -> List[Path]:
    out_dir = (repo_root_path / "out").resolve()
    work_dir = (repo_root_path / "work").resolve()
    seen: set[Path] = set()
    discovered: List[Path] = []
    for path in sorted(input_dir.rglob("*.docx")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        if (
            is_under(resolved, output_root)
            or is_under(resolved, out_dir)
            or is_under(resolved, work_dir)
        ):
            continue
        if any(part.lower().endswith("_files") for part in resolved.parts):
            continue
        seen.add(resolved)
        discovered.append(resolved)
    return discovered


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def detect_subject(raw_name: str) -> str:
    if not raw_name:
        return "generic"
    ascii_name = unicodedata.normalize("NFD", raw_name)
    ascii_name = "".join(ch for ch in ascii_name if unicodedata.category(ch) != "Mn")
    tokens = set(re.sub(r"[^a-z0-9]+", " ", ascii_name.lower()).split())
    if {"hoa", "chem", "chemistry"} & tokens:
        return "chemistry"
    if "ly" in tokens or {"phys", "physics"} & tokens or {"vat", "ly"} <= tokens:
        return "physics"
    if {"toan", "math"} & tokens:
        return "math"
    if {"sinh", "bio", "biology"} & tokens:
        return "biology"
    return "generic"


def default_project_jar(root: Path) -> Path:
    matches = sorted(root.glob("target/*-jar-with-dependencies.jar"))
    if not matches:
        raise FileNotFoundError(
            "No jar-with-dependencies found under target/. Run mvn package first."
        )
    return matches[-1]


def default_saxon_jar(root: Path) -> Path:
    matches = sorted((root / "tools/calabash/distro/lib").glob("Saxon-HE*.jar"))
    if not matches:
        raise FileNotFoundError(
            "No Saxon-HE jar found under tools/calabash/distro/lib/."
        )
    return matches[-1]


def run_command(
    cmd: List[str], cwd: Path, log_path: Path, env: Dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    combined = (
        (result.stdout or "")
        + ("\n" if result.stdout and result.stderr else "")
        + (result.stderr or "")
    )
    log_path.write_text(combined, encoding="utf-8")
    return result


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_fingerprint(path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        stat = path.stat()
    except FileNotFoundError:
        return "missing"
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def file_sha256(path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError:
        return "missing"


def compute_conversion_fingerprint(
    *,
    docx_path: Path,
    subject: str,
    project_jar: Path,
    mathtype_dir: Path,
    xmlcalabash_jar: Path,
    saxon_jar: Path,
    transpect_config: Path,
    wrapper_script: Path,
    qa_script: Path,
) -> str:
    payload = {
        "docx": str(docx_path.resolve()),
        "docx_fp": file_fingerprint(docx_path.resolve()),
        "docx_sha256": file_sha256(docx_path.resolve()),
        "subject": subject,
        "project_jar": str(project_jar.resolve()),
        "project_jar_fp": file_fingerprint(project_jar.resolve()),
        "mathtype_dir": str(mathtype_dir.resolve()),
        "mathtype_dir_fp": file_fingerprint(mathtype_dir.resolve()),
        "xmlcalabash_jar": str(xmlcalabash_jar.resolve()),
        "xmlcalabash_jar_fp": file_fingerprint(xmlcalabash_jar.resolve()),
        "saxon_jar": str(saxon_jar.resolve()),
        "saxon_jar_fp": file_fingerprint(saxon_jar.resolve()),
        "transpect_config": str(transpect_config.resolve()),
        "transpect_config_fp": file_fingerprint(transpect_config.resolve()),
        "wrapper_script_fp": file_fingerprint(wrapper_script.resolve()),
        "wrapper_script_sha256": file_sha256(wrapper_script.resolve()),
        "qa_script_fp": file_fingerprint(qa_script.resolve()),
        "qa_script_sha256": file_sha256(qa_script.resolve()),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_tsv_timing(path: Path) -> Dict[str, float]:
    timings: Dict[str, float] = {}
    if not path.exists():
        return timings
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        if key == "phase":
            continue
        try:
            timings[key.strip()] = float(value.strip())
        except ValueError:
            continue
    return timings


def latest_source_mtime_ns(root: Path) -> int:
    max_ns = 0
    candidates = [
        root / "pom.xml",
        root / "src" / "main" / "java",
        root / "src" / "main" / "resources",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if candidate.is_file():
            max_ns = max(max_ns, candidate.stat().st_mtime_ns)
            continue
        for path in candidate.rglob("*"):
            if path.is_file():
                max_ns = max(max_ns, path.stat().st_mtime_ns)
    return max_ns


def build_markdown(summary: Dict) -> str:
    lines: List[str] = []
    lines.append("# Subject Batch Summary")
    lines.append("")
    lines.append(f"- Batch: `{summary['batch_name']}`")
    lines.append(f"- Generated at: `{summary['generated_at']}`")
    lines.append(f"- Input dir: `{summary['input_dir']}`")
    lines.append(f"- Output dir: `{summary['output_dir']}`")
    lines.append(f"- Work dir: `{summary['work_dir']}`")
    lines.append(f"- Publish verdict: `{summary['publish_verdict']}`")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    totals = summary["totals"]
    lines.append(f"- Documents discovered: {totals['documents_discovered']}")
    lines.append(f"- Documents converted: {totals['documents_converted']}")
    lines.append(f"- Documents failed: {totals['documents_failed']}")
    lines.append(f"- MathML formulas: {totals['mathml_formulas']}")
    lines.append(f"- Remaining preview images: {totals['remaining_preview_images']}")
    lines.append(
        f"- Remaining text corruption count: {totals['remaining_text_corruption_count']}"
    )
    lines.append(
        f"- Remaining chemistry inline issues: {totals['remaining_chemistry_inline_issues']}"
    )
    lines.append(f"- Chemistry inline fixes: {totals['chemistry_inline_fixes']}")
    lines.append("")
    perf = summary.get("performance", {})
    if perf:
        lines.append("## Performance")
        lines.append("")
        lines.append(f"- Build executed: {perf.get('build_executed', False)}")
        lines.append(
            f"- Documents reused from cache: {perf.get('documents_reused', 0)}"
        )
        lines.append(f"- Documents reconverted: {perf.get('documents_reconverted', 0)}")
        lines.append(
            f"- Conversion wall seconds: {perf.get('conversion_wall_seconds', 0.0):.3f}"
        )
        lines.append(f"- QA wall seconds: {perf.get('qa_wall_seconds', 0.0):.3f}")
        lines.append(
            f"- Sidecar generation seconds: {perf.get('sidecar_generation_seconds', 0.0):.3f}"
        )
        lines.append(
            f"- Java conversion seconds: {perf.get('java_conversion_seconds', 0.0):.3f}"
        )
        lines.append("")
    lines.append("## Count By Type")
    lines.append("")
    lines.append("| type | count |")
    lines.append("|---|---:|")
    for key in TYPE_KEYS:
        lines.append(f"| `{key}` | {summary['count_by_type'][key]} |")
    lines.append("")
    lines.append("## By Subject")
    lines.append("")
    lines.append("| subject | count |")
    lines.append("|---|---:|")
    for subject, count in sorted(summary["by_subject"].items()):
        lines.append(f"| `{subject}` | {count} |")
    lines.append("")
    lines.append("## Files")
    lines.append("")
    lines.append(
        "| source | subject | status | reused | conv(s) | qa(s) | mathml | previews | corruption | chem inline issues | verdict | html | qa json |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|")
    for item in summary["files"]:
        if item["status"] != "ok":
            lines.append(
                f"| `{item['source_relative']}` | `{item['subject']}` | failed |  | 0 | 0 | 0 | 0 | 0 | 0 | `failed` |  |  |"
            )
            continue
        totals = item["qa"]["totals"]
        lines.append(
            "| `{}` | `{}` | ok | `{}` | {:.3f} | {:.3f} | {} | {} | {} | {} | `{}` | `{}` | `{}` |".format(
                item["source_relative"],
                item["subject"],
                "yes" if item.get("reused", False) else "no",
                float(item.get("conversion_seconds", 0.0)),
                float(item.get("qa_seconds", 0.0)),
                totals["mathml_formulas"],
                totals["remaining_preview_images"],
                totals["remaining_text_corruption_count"],
                totals["remaining_chemistry_inline_issues"],
                item["qa"]["publish_verdict"],
                item["html_relative"],
                item["qa_json_relative"],
            )
        )
    lines.append("")
    failures = [item for item in summary["files"] if item["status"] != "ok"]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            lines.append(f"- `{item['source_relative']}`: {item['error']}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    root = repo_root()
    default_batch_name = "subject-profiles-v1-" + datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    parser = argparse.ArgumentParser(
        description="Run deterministic single-pass DOCX -> HTML conversion with optional legacy recursive discovery."
    )
    parser.add_argument(
        "--input-docx",
        type=Path,
        default=None,
        help="Explicit single source DOCX to convert.",
    )
    parser.add_argument("--input-dir", type=Path, default=root / "in")
    parser.add_argument(
        "--allow-recursive-discovery",
        action="store_true",
        help="Allow legacy recursive scan under --input-dir. Disabled by default.",
    )
    parser.add_argument("--output-root", type=Path, default=root / "out")
    parser.add_argument("--batch-name", default=default_batch_name)
    parser.add_argument("--project-jar", type=Path, default=None)
    parser.add_argument(
        "--mathtype-dir",
        type=Path,
        default=root / "tools/calabash/extensions/transpect/mathtype-extension",
    )
    parser.add_argument(
        "--xmlcalabash-jar",
        type=Path,
        default=root / "tools/calabash/distro/xmlcalabash-1.4.1-100.jar",
    )
    parser.add_argument("--saxon-jar", type=Path, default=None)
    parser.add_argument(
        "--transpect-config",
        type=Path,
        default=root / "tools/calabash/extensions/transpect/transpect-config.xml",
    )
    parser.add_argument(
        "--subject",
        choices=["generic", "physics", "chemistry", "math", "biology"],
        default=None,
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument(
        "--reuse-if-unchanged", dest="reuse_if_unchanged", action="store_true"
    )
    parser.add_argument("--no-reuse", dest="reuse_if_unchanged", action="store_false")
    parser.set_defaults(reuse_if_unchanged=True)
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_root = args.output_root.resolve()
    project_jar = (
        args.project_jar.resolve() if args.project_jar else default_project_jar(root)
    )
    saxon_jar = args.saxon_jar.resolve() if args.saxon_jar else default_saxon_jar(root)
    batch_dir = output_root / args.batch_name
    html_root = batch_dir / "html"
    qa_root = batch_dir / "qa"
    logs_root = batch_dir / "logs"
    work_root = (root / "work" / "batches" / args.batch_name).resolve()

    for path in (html_root, qa_root, logs_root, work_root):
        path.mkdir(parents=True, exist_ok=True)

    build_log = logs_root / "build.log"
    build_executed = False
    if not args.skip_build:
        need_build = args.force_build
        if not need_build:
            if not project_jar.exists():
                need_build = True
            else:
                newest_source_ns = latest_source_mtime_ns(root)
                need_build = project_jar.stat().st_mtime_ns < newest_source_ns
        if need_build:
            build_result = run_command(
                ["mvn", "-q", "-DskipTests", "package"], root, build_log
            )
            build_executed = True
            if build_result.returncode != 0:
                raise SystemExit(f"Build failed. See {build_log}")
        else:
            build_log.write_text(
                "Build skipped: output jar newer than source tree.\n", encoding="utf-8"
            )

    wrapper_script = root / "scripts/transpect/run_docx_with_transpect.sh"
    qa_script = root / "scripts/qa/audit_exam_bundle.py"
    explicit_input = args.input_docx.resolve() if args.input_docx else None
    if explicit_input is not None:
        if explicit_input.suffix.lower() != ".docx":
            raise SystemExit(f"Explicit input must be a .docx file: {explicit_input}")
        if not explicit_input.is_file():
            raise SystemExit(f"Explicit input not found: {explicit_input}")
        if (
            is_under(explicit_input, output_root)
            or is_under(explicit_input, root / "out")
            or is_under(explicit_input, root / "work")
        ):
            raise SystemExit(
                f"Explicit input cannot be under output/work directories: {explicit_input}"
            )
        docx_files = [explicit_input]
    elif args.allow_recursive_discovery:
        docx_files = discover_docx_inputs(input_dir, output_root, root)
        if not docx_files:
            raise SystemExit(f"No .docx source files found under {input_dir}")
    else:
        raise SystemExit(
            "Refusing recursive discovery by default. Provide --input-docx <file.docx> "
            "or use --allow-recursive-discovery explicitly."
        )

    files: List[Dict] = []
    by_subject: Counter[str] = Counter()
    aggregate_totals = {
        "documents_discovered": len(docx_files),
        "documents_converted": 0,
        "documents_failed": 0,
        "mathml_formulas": 0,
        "remaining_preview_images": 0,
        "remaining_text_corruption_count": 0,
        "remaining_chemistry_inline_issues": 0,
        "chemistry_inline_fixes": 0,
    }
    count_by_type = {key: 0 for key in TYPE_KEYS}
    performance_totals = {
        "build_executed": build_executed,
        "documents_reused": 0,
        "documents_reconverted": 0,
        "conversion_wall_seconds": 0.0,
        "qa_wall_seconds": 0.0,
        "sidecar_generation_seconds": 0.0,
        "java_conversion_seconds": 0.0,
    }

    for docx_path in docx_files:
        try:
            rel_docx = docx_path.resolve().relative_to(input_dir)
        except ValueError:
            rel_docx = Path(docx_path.name)
        rel_stem = rel_docx.with_suffix("")
        subject = args.subject or detect_subject(docx_path.name)
        by_subject[subject] += 1

        html_path = (html_root / rel_stem).with_name(rel_stem.name + "-transpect.html")
        qa_json = (qa_root / rel_stem).with_name(rel_stem.name + ".qa.json")
        qa_md = (qa_root / rel_stem).with_name(rel_stem.name + ".qa.md")
        conversion_log = (logs_root / rel_stem).with_name(
            rel_stem.name + ".conversion.log"
        )
        qa_log = (logs_root / rel_stem).with_name(rel_stem.name + ".qa.log")
        work_dir = work_root / rel_stem
        cache_meta = work_dir / ".conversion-cache.json"

        html_path.parent.mkdir(parents=True, exist_ok=True)
        qa_json.parent.mkdir(parents=True, exist_ok=True)
        conversion_log.parent.mkdir(parents=True, exist_ok=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        conversion_fingerprint = compute_conversion_fingerprint(
            docx_path=docx_path,
            subject=subject,
            project_jar=project_jar,
            mathtype_dir=args.mathtype_dir.resolve(),
            xmlcalabash_jar=args.xmlcalabash_jar.resolve(),
            saxon_jar=saxon_jar,
            transpect_config=args.transpect_config.resolve(),
            wrapper_script=wrapper_script,
            qa_script=qa_script,
        )
        can_reuse = False
        if (
            args.reuse_if_unchanged
            and cache_meta.exists()
            and html_path.exists()
            and qa_json.exists()
            and qa_md.exists()
        ):
            try:
                meta_payload = load_json(cache_meta)
                can_reuse = meta_payload.get("fingerprint") == conversion_fingerprint
            except Exception:
                can_reuse = False

        convert_cmd = [
            str(wrapper_script),
            str(docx_path.resolve()),
            str(html_path),
            str(project_jar),
            str(args.mathtype_dir.resolve()),
            str(args.xmlcalabash_jar.resolve()),
            str(saxon_jar),
            str(work_dir),
            str(args.transpect_config.resolve()),
            "--subject",
            subject,
        ]
        cache_dir = work_root / ".cache" / "docx-html-math" / "transpect-sidecars"
        cache_dir.mkdir(parents=True, exist_ok=True)
        convert_env = os.environ.copy()
        convert_env["DOCX_MATH_CACHE_DIR"] = str(cache_dir)
        conversion_seconds = 0.0
        qa_seconds = 0.0
        run_timings: Dict[str, float] = {}
        if can_reuse:
            performance_totals["documents_reused"] += 1
        else:
            performance_totals["documents_reconverted"] += 1
            convert_start = time.perf_counter()
            convert_result = run_command(
                convert_cmd, root, conversion_log, env=convert_env
            )
            conversion_seconds = time.perf_counter() - convert_start
            performance_totals["conversion_wall_seconds"] += conversion_seconds
            if convert_result.returncode != 0:
                aggregate_totals["documents_failed"] += 1
                files.append(
                    {
                        "source": str(docx_path.resolve()),
                        "source_relative": str(rel_docx),
                        "subject": subject,
                        "status": "failed",
                        "error": f"conversion failed with exit code {convert_result.returncode}",
                        "conversion_log": str(conversion_log.resolve()),
                    }
                )
                continue

            asset_dir = html_path.with_name(html_path.stem + "_files")
            qa_cmd = [
                sys.executable,
                str(qa_script),
                str(html_path),
                "--asset-dir",
                str(asset_dir),
                "--conversion-log",
                str(conversion_log),
                "--subject",
                subject,
                "--json-out",
                str(qa_json),
                "--md-out",
                str(qa_md),
            ]
            qa_start = time.perf_counter()
            qa_result = run_command(qa_cmd, root, qa_log)
            qa_seconds = time.perf_counter() - qa_start
            performance_totals["qa_wall_seconds"] += qa_seconds
            if qa_result.returncode != 0:
                aggregate_totals["documents_failed"] += 1
                files.append(
                    {
                        "source": str(docx_path.resolve()),
                        "source_relative": str(rel_docx),
                        "subject": subject,
                        "status": "failed",
                        "error": f"qa failed with exit code {qa_result.returncode}",
                        "conversion_log": str(conversion_log.resolve()),
                        "qa_log": str(qa_log.resolve()),
                    }
                )
                continue

            cache_meta.write_text(
                json.dumps(
                    {
                        "fingerprint": conversion_fingerprint,
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                        "html": str(html_path.resolve()),
                        "qa_json": str(qa_json.resolve()),
                        "qa_md": str(qa_md.resolve()),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        try:
            report = load_json(qa_json)
        except Exception as ex:
            aggregate_totals["documents_failed"] += 1
            files.append(
                {
                    "source": str(docx_path.resolve()),
                    "source_relative": str(rel_docx),
                    "subject": subject,
                    "status": "failed",
                    "error": f"unable to read QA json: {ex}",
                    "conversion_log": str(conversion_log.resolve()),
                    "qa_log": str(qa_log.resolve()),
                }
            )
            continue
        run_timings = read_tsv_timing(work_dir / "run.timings.tsv")
        if not can_reuse:
            performance_totals["sidecar_generation_seconds"] += run_timings.get(
                "sidecar-generation", 0.0
            )
            performance_totals["java_conversion_seconds"] += run_timings.get(
                "java-conversion", 0.0
            )
        totals = report["totals"]
        aggregate_totals["documents_converted"] += 1
        aggregate_totals["mathml_formulas"] += totals["mathml_formulas"]
        aggregate_totals["remaining_preview_images"] += totals[
            "remaining_preview_images"
        ]
        aggregate_totals["remaining_text_corruption_count"] += totals[
            "remaining_text_corruption_count"
        ]
        aggregate_totals["remaining_chemistry_inline_issues"] += totals[
            "remaining_chemistry_inline_issues"
        ]
        aggregate_totals["chemistry_inline_fixes"] += totals["chemistry_inline_fixes"]
        for key in TYPE_KEYS:
            count_by_type[key] += report["count_by_type"].get(key, 0)

        files.append(
            {
                "source": str(docx_path.resolve()),
                "source_relative": str(rel_docx),
                "subject": subject,
                "status": "ok",
                "html": str(html_path.resolve()),
                "html_relative": str(html_path.resolve().relative_to(batch_dir)),
                "qa_json": str(qa_json.resolve()),
                "qa_json_relative": str(qa_json.resolve().relative_to(batch_dir)),
                "qa_md": str(qa_md.resolve()),
                "conversion_log": str(conversion_log.resolve()),
                "qa_log": str(qa_log.resolve()),
                "work_dir": str(work_dir.resolve()),
                "reused": can_reuse,
                "conversion_seconds": conversion_seconds,
                "qa_seconds": qa_seconds,
                "run_timings": run_timings,
                "qa": report,
            }
        )

    publish_verdict = "safe to publish"
    if aggregate_totals["documents_failed"] or any(
        item.get("qa", {}).get("publish_verdict") != "safe to publish"
        for item in files
        if item["status"] == "ok"
    ):
        publish_verdict = "still needs cleanup"

    summary = {
        "batch_name": args.batch_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "output_dir": str(batch_dir),
        "work_dir": str(work_root),
        "publish_verdict": publish_verdict,
        "totals": aggregate_totals,
        "performance": performance_totals,
        "count_by_type": count_by_type,
        "by_subject": dict(sorted(by_subject.items())),
        "files": files,
    }

    batch_json = batch_dir / "batch-summary.json"
    batch_md = batch_dir / "batch-summary.md"
    batch_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    batch_md.write_text(build_markdown(summary), encoding="utf-8")

    print(batch_dir)


if __name__ == "__main__":
    main()
