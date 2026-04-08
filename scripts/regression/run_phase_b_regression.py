#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CATEGORY_KEYS = [
    "unzip_load",
    "omml_conversion",
    "sidecar_generation",
    "image_rendering",
    "cleanup_sanitize",
    "parser_json_build",
    "write_output",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(cmd: List[str], cwd: Path, log_path: Path, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    combined = (result.stdout or "") + ("\n" if result.stdout and result.stderr else "") + (result.stderr or "")
    log_path.write_text(combined, encoding="utf-8")
    return result


def default_project_jar(root: Path) -> Path:
    matches = sorted(root.glob("target/*-jar-with-dependencies.jar"))
    if not matches:
        raise FileNotFoundError("No jar-with-dependencies found under target/. Run mvn package first.")
    return matches[-1]


def default_saxon_jar(root: Path) -> Path:
    candidates = sorted((root / "tools/calabash/distro/lib").glob("Saxon-HE*.jar"))
    if candidates:
        return candidates[-1]
    fallback = root / "tools/calabash/saxon/saxon10he.jar"
    if fallback.exists():
        return fallback
    raise FileNotFoundError("No Saxon HE jar found in tools/calabash/distro/lib or tools/calabash/saxon.")


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


def compute_fingerprint(
    *,
    source_docx: Path,
    subject: str,
    output_mode: str,
    project_jar: Path,
    mathtype_dir: Path,
    xmlcalabash_jar: Path,
    saxon_jar: Path,
    transpect_config: Path,
    wrapper_script: Path,
    qa_script: Path,
    contract_script: Path,
    converter_file: Path,
    parser_contract_file: Path,
    override_manifest: Optional[Path],
) -> str:
    payload = {
        "source_docx": str(source_docx.resolve()),
        "source_docx_fp": file_fingerprint(source_docx.resolve()),
        "source_docx_sha256": file_sha256(source_docx.resolve()),
        "subject": subject,
        "output_mode": output_mode,
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
        "wrapper_script_sha256": file_sha256(wrapper_script.resolve()),
        "qa_script_sha256": file_sha256(qa_script.resolve()),
        "contract_script_sha256": file_sha256(contract_script.resolve()),
        "converter_file_sha256": file_sha256(converter_file.resolve()),
        "parser_contract_file_sha256": file_sha256(parser_contract_file.resolve()),
        "override_manifest": str(override_manifest.resolve()) if override_manifest else "",
        "override_manifest_fp": file_fingerprint(override_manifest.resolve()) if override_manifest else "none",
        "override_manifest_sha256": file_sha256(override_manifest.resolve()) if override_manifest else "none",
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_tsv(path: Path) -> Dict[str, float]:
    values: Dict[str, float] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        if key == "phase":
            continue
        try:
            values[key.strip()] = float(value.strip())
        except ValueError:
            continue
    return values


def parse_converter_timing_ms(conversion_log: Path) -> Dict[str, float]:
    result = {
        "docx_load_ms": 0.0,
        "omml_handling_ms": 0.0,
        "image_rendering_ms": 0.0,
        "html_cleanup_ms": 0.0,
        "publish_sanitize_ms": 0.0,
        "html_write_ms": 0.0,
    }
    if not conversion_log.exists():
        return result
    text = conversion_log.read_text(encoding="utf-8", errors="ignore")
    patterns = {
        "docx_load_ms": r"DOCX load:\s*(\d+)",
        "omml_handling_ms": r"OMML handling:\s*(\d+)",
        "image_rendering_ms": r"Image/diagram rendering:\s*(\d+)",
        "html_cleanup_ms": r"HTML cleanup:\s*(\d+)",
        "publish_sanitize_ms": r"Publish sanitize:\s*(\d+)",
        "html_write_ms": r"HTML write:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text)
        if m:
            result[key] = float(m.group(1))
    return result


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    sorted_values = sorted(values)
    idx = (len(sorted_values) - 1) * p
    lower = int(idx)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return float(sorted_values[lower])
    fraction = idx - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def merge_thresholds(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_thresholds(merged[key], value)
        else:
            merged[key] = value
    return merged


def evaluate_parser_gate(
    *,
    parser_summary: Dict[str, Any],
    subject: str,
    category: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    subject_thresholds = config.get("subject_thresholds", {})
    subject_cfg = subject_thresholds.get(subject, subject_thresholds.get("generic", {})) if isinstance(subject_thresholds, dict) else {}
    category_cfg = config.get("category_overrides", {}).get(category, {}) if isinstance(config.get("category_overrides", {}), dict) else {}
    effective = merge_thresholds(subject_cfg if isinstance(subject_cfg, dict) else {}, category_cfg if isinstance(category_cfg, dict) else {})
    global_cfg = config.get("global", {}) if isinstance(config.get("global", {}), dict) else {}

    question_count = int(parser_summary.get("question_count", 0) or 0)
    warning_count = int(parser_summary.get("warning_count", 0) or 0)
    unknown_count = int(parser_summary.get("unknown_question_type_count", 0) or 0)
    orphan_assets = int(parser_summary.get("orphan_asset_count", 0) or 0)
    orphan_math = int(parser_summary.get("orphan_math_fragment_count", 0) or 0)
    avg_conf = float(parser_summary.get("avg_confidence", 0.0) or 0.0)
    answer_blockers = int(parser_summary.get("answer_blocker_count", 0) or 0)
    canonical_missing = int(parser_summary.get("canonical_answer_missing_count", 0) or 0)
    answer_conflicts = int(parser_summary.get("answer_conflict_count", 0) or 0)
    unresolved_reconciliation = int(parser_summary.get("unresolved_reconciliation_count", 0) or 0)

    unknown_ratio = (unknown_count / question_count) if question_count > 0 else 0.0
    warning_per_question = (warning_count / question_count) if question_count > 0 else 0.0

    hard_failures: List[str] = []
    review_findings: List[str] = []
    allow_zero_questions = bool(effective.get("allow_zero_questions", False))
    min_question_count = int(effective.get("min_question_count", 0) or 0)
    if question_count == 0 and not allow_zero_questions:
        hard_failures.append("question_count is 0 while allow_zero_questions=false")
    if question_count > 0 and min_question_count > 0 and question_count < min_question_count:
        hard_failures.append(f"question_count {question_count} < min_question_count {min_question_count}")

    min_avg_conf = effective.get("min_avg_confidence")
    if isinstance(min_avg_conf, (int, float)) and question_count > 0 and avg_conf < float(min_avg_conf):
        hard_failures.append(f"avg_confidence {avg_conf:.3f} < min_avg_confidence {float(min_avg_conf):.3f}")

    max_unknown_ratio = effective.get("max_unknown_question_type_ratio")
    if isinstance(max_unknown_ratio, (int, float)) and question_count > 0 and unknown_ratio > float(max_unknown_ratio):
        hard_failures.append(
            f"unknown_question_type_ratio {unknown_ratio:.3f} > max_unknown_question_type_ratio {float(max_unknown_ratio):.3f}"
        )

    max_warning_per_question = effective.get("max_warning_per_question")
    if isinstance(max_warning_per_question, (int, float)) and question_count > 0 and warning_per_question > float(max_warning_per_question):
        review_findings.append(
            f"warning_per_question {warning_per_question:.3f} > review_max_warning_per_question {float(max_warning_per_question):.3f}"
        )

    max_orphan_asset = int(
        (
            effective.get("max_orphan_asset_count")
            if effective.get("max_orphan_asset_count") is not None
            else global_cfg.get("max_orphan_asset_count", 10**9)
        )
        or 0
    )
    if orphan_assets > max_orphan_asset:
        hard_failures.append(f"orphan_asset_count {orphan_assets} > max_orphan_asset_count {max_orphan_asset}")

    max_orphan_math = int(
        (
            effective.get("max_orphan_math_fragment_count")
            if effective.get("max_orphan_math_fragment_count") is not None
            else global_cfg.get("max_orphan_math_fragment_count", 10**9)
        )
        or 0
    )
    if orphan_math > max_orphan_math:
        hard_failures.append(f"orphan_math_fragment_count {orphan_math} > max_orphan_math_fragment_count {max_orphan_math}")

    max_answer_blockers = int(
        (
            effective.get("max_answer_blocker_count")
            if effective.get("max_answer_blocker_count") is not None
            else global_cfg.get("max_answer_blocker_count", 10**9)
        )
        or 0
    )
    if answer_blockers > max_answer_blockers:
        hard_failures.append(f"answer_blocker_count {answer_blockers} > max_answer_blocker_count {max_answer_blockers}")

    max_canonical_missing = int(
        (
            effective.get("max_canonical_answer_missing_count")
            if effective.get("max_canonical_answer_missing_count") is not None
            else global_cfg.get("max_canonical_answer_missing_count", 10**9)
        )
        or 0
    )
    if canonical_missing > max_canonical_missing:
        hard_failures.append(
            f"canonical_answer_missing_count {canonical_missing} > max_canonical_answer_missing_count {max_canonical_missing}"
        )

    max_answer_conflicts = int(
        (
            effective.get("max_answer_conflict_count")
            if effective.get("max_answer_conflict_count") is not None
            else global_cfg.get("max_answer_conflict_count", 10**9)
        )
        or 0
    )
    if answer_conflicts > max_answer_conflicts:
        hard_failures.append(f"answer_conflict_count {answer_conflicts} > max_answer_conflict_count {max_answer_conflicts}")

    max_unresolved_reconciliation = int(
        (
            effective.get("max_unresolved_reconciliation_count")
            if effective.get("max_unresolved_reconciliation_count") is not None
            else global_cfg.get("max_unresolved_reconciliation_count", 10**9)
        )
        or 0
    )
    if unresolved_reconciliation > max_unresolved_reconciliation:
        hard_failures.append(
            "unresolved_reconciliation_count "
            f"{unresolved_reconciliation} > max_unresolved_reconciliation_count {max_unresolved_reconciliation}"
        )

    return {
        "passed": len(hard_failures) == 0,
        "review_required": len(review_findings) > 0,
        "hard_failures": hard_failures,
        "review_findings": review_findings,
        "failures": hard_failures,
        "warnings": review_findings,
        "status": "failed" if hard_failures else ("passed_with_review" if review_findings else "passed"),
        "metrics": {
            "question_count": question_count,
            "warning_count": warning_count,
            "unknown_question_type_count": unknown_count,
            "unknown_question_type_ratio": round(unknown_ratio, 6),
            "warning_per_question": round(warning_per_question, 6),
            "avg_confidence": round(avg_conf, 6),
            "orphan_asset_count": orphan_assets,
            "orphan_math_fragment_count": orphan_math,
            "answer_blocker_count": answer_blockers,
            "canonical_answer_missing_count": canonical_missing,
            "answer_conflict_count": answer_conflicts,
            "unresolved_reconciliation_count": unresolved_reconciliation,
        },
        "thresholds": {
            "min_question_count": min_question_count,
            "allow_zero_questions": allow_zero_questions,
            "min_avg_confidence": effective.get("min_avg_confidence"),
            "max_unknown_question_type_ratio": effective.get("max_unknown_question_type_ratio"),
            "max_warning_per_question": effective.get("max_warning_per_question"),
            "max_orphan_asset_count": max_orphan_asset,
            "max_orphan_math_fragment_count": max_orphan_math,
            "max_answer_blocker_count": max_answer_blockers,
            "max_canonical_answer_missing_count": max_canonical_missing,
            "max_answer_conflict_count": max_answer_conflicts,
            "max_unresolved_reconciliation_count": max_unresolved_reconciliation,
        },
    }


def evaluate_performance_gates(
    *,
    report: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    aggregate = report.get("category_aggregate", {})
    aggregate_limits = config.get("aggregate_limits", {}) if isinstance(config.get("aggregate_limits", {}), dict) else {}
    for category, limits in aggregate_limits.items():
        if not isinstance(limits, dict):
            continue
        stats = aggregate.get(category, {})
        if not isinstance(stats, dict):
            continue
        p90_max = limits.get("p90_seconds_max")
        if isinstance(p90_max, (int, float)):
            actual_p90 = float(stats.get("p90_seconds", 0.0) or 0.0)
            if actual_p90 > float(p90_max):
                failures.append(
                    {
                        "scope": "aggregate",
                        "category": category,
                        "metric": "p90_seconds",
                        "actual": actual_p90,
                        "limit": float(p90_max),
                    }
                )
        total_max = limits.get("total_seconds_max")
        if isinstance(total_max, (int, float)):
            actual_total = float(stats.get("total_seconds", 0.0) or 0.0)
            if actual_total > float(total_max):
                failures.append(
                    {
                        "scope": "aggregate",
                        "category": category,
                        "metric": "total_seconds",
                        "actual": actual_total,
                        "limit": float(total_max),
                    }
                )

    base_sample_limits = config.get("sample_limits", {}) if isinstance(config.get("sample_limits", {}), dict) else {}
    category_overrides = config.get("category_overrides", {}) if isinstance(config.get("category_overrides", {}), dict) else {}
    for sample in report.get("samples", []):
        if sample.get("status") not in {"ok", "passed_with_review"}:
            continue
        category = str(sample.get("category", "unknown"))
        category_sample_limits = (
            category_overrides.get(category, {}).get("sample_limits", {})
            if isinstance(category_overrides.get(category, {}), dict)
            else {}
        )
        effective_sample_limits = merge_thresholds(base_sample_limits, category_sample_limits if isinstance(category_sample_limits, dict) else {})
        timing = sample.get("timing_categories", {})
        for metric_category, metric_limits in effective_sample_limits.items():
            if not isinstance(metric_limits, dict):
                continue
            seconds_max = metric_limits.get("seconds_max")
            if not isinstance(seconds_max, (int, float)):
                continue
            actual_seconds = float(timing.get(metric_category, 0.0) or 0.0)
            if actual_seconds > float(seconds_max):
                failures.append(
                    {
                        "scope": "sample",
                        "sample_id": sample.get("sample_id", ""),
                        "category": metric_category,
                        "metric": "seconds",
                        "actual": actual_seconds,
                        "limit": float(seconds_max),
                    }
                )

    return {"passed": len(failures) == 0, "failures": failures}


def build_baseline_markdown(report: Dict) -> str:
    lines: List[str] = []
    lines.append("# Phase B Performance Baseline")
    lines.append("")
    lines.append(f"- Run name: `{report['run_name']}`")
    lines.append(f"- Generated at: `{report['generated_at']}`")
    lines.append(f"- Inventory: `{report['inventory_path']}`")
    lines.append(f"- Cache dir: `{report.get('cache_dir', '')}`")
    lines.append(f"- Sample count: {report['sample_count']}")
    lines.append(f"- Needs review: `{report.get('needs_review_count', 0)}`")
    lines.append("")
    lines.append("## Timing Categories")
    lines.append("")
    lines.append("| category | total (s) | mean (s) | median (s) | p90 (s) |")
    lines.append("|---|---:|---:|---:|---:|")
    for key in CATEGORY_KEYS:
        agg = report["category_aggregate"].get(key, {})
        lines.append(
            f"| `{key}` | {agg.get('total_seconds', 0.0):.3f} | {agg.get('mean_seconds', 0.0):.3f} | {agg.get('median_seconds', 0.0):.3f} | {agg.get('p90_seconds', 0.0):.3f} |"
        )
    lines.append("")
    gate_summary = report.get("gates", {})
    lines.append("## Gates")
    lines.append("")
    lines.append(f"- Parser gate passed: `{bool(gate_summary.get('parser_gate_passed', False))}`")
    lines.append(f"- Parser review findings: `{len(gate_summary.get('review_findings', [])) if isinstance(gate_summary.get('review_findings', []), list) else 0}`")
    lines.append(f"- Contract compatibility gate passed: `{bool(gate_summary.get('contract_gate_passed', False))}`")
    lines.append(f"- Performance gate passed: `{bool(gate_summary.get('performance_gate_passed', False))}`")
    lines.append("")
    if gate_summary.get("failures"):
        lines.append("| gate | scope | target | metric | actual | limit |")
        lines.append("|---|---|---|---|---:|---:|")
        for failure in gate_summary.get("failures", []):
            lines.append(
                "| {} | {} | {} | {} | {} | {} |".format(
                    failure.get("gate", ""),
                    failure.get("scope", ""),
                    failure.get("target", ""),
                    failure.get("metric", ""),
                    failure.get("actual", ""),
                    failure.get("limit", ""),
                )
            )
        lines.append("")

    lines.append("## Samples")
    lines.append("")
    lines.append("| sample_id | category | subject | status | reused | parser gate | contract gate | unzip/load | omml | sidecar | image | cleanup/sanitize | parser | write | parser avg confidence | parser warnings |")
    lines.append("|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for item in report["samples"]:
        timing = item.get("timing_categories", {})
        parser_summary = item.get("parser_summary", {})
        parser_gate = item.get("parser_gate", {})
        contract_gate = item.get("contract_gate", {})
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {} |".format(
                item.get("sample_id", ""),
                item.get("category", ""),
                item.get("subject", ""),
                item.get("status", "failed"),
                "yes" if item.get("reused", False) else "no",
                "pass" if parser_gate.get("passed") else "fail",
                "pass" if contract_gate.get("passed") else "fail",
                float(timing.get("unzip_load", 0.0)),
                float(timing.get("omml_conversion", 0.0)),
                float(timing.get("sidecar_generation", 0.0)),
                float(timing.get("image_rendering", 0.0)),
                float(timing.get("cleanup_sanitize", 0.0)),
                float(timing.get("parser_json_build", 0.0)),
                float(timing.get("write_output", 0.0)),
                float(parser_summary.get("avg_confidence", 0.0)),
                int(parser_summary.get("warning_count", 0) or 0),
            )
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    root = repo_root()
    parser = argparse.ArgumentParser(description="Run Phase B regression set and generate performance baseline.")
    parser.add_argument("--inventory", type=Path, default=root / "regression_set/phase_b_inventory.json")
    parser.add_argument("--output-root", type=Path, default=root / "out")
    parser.add_argument("--run-name", default="phase-b-regression-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--project-jar", type=Path, default=None)
    parser.add_argument("--mathtype-dir", type=Path, default=root / "tools/calabash/extensions/transpect/mathtype-extension")
    parser.add_argument("--xmlcalabash-jar", type=Path, default=root / "tools/calabash/distro/xmlcalabash-1.4.1-100.jar")
    parser.add_argument("--saxon-jar", type=Path, default=None)
    parser.add_argument("--transpect-config", type=Path, default=root / "tools/calabash/extensions/transpect/transpect-config.xml")
    parser.add_argument("--output-mode", choices=["internal", "publish"], default="publish")
    parser.add_argument("--override-manifest", type=Path, default=None)
    parser.add_argument("--parser-gate-config", type=Path, default=root / "regression_set/parser_quality_gate_v1.json")
    parser.add_argument("--perf-gate-config", type=Path, default=root / "regression_set/performance_gate_v1.json")
    parser.add_argument("--contract-gate-config", type=Path, default=root / "scripts/contracts/contract_compatibility_v1.json")
    parser.add_argument("--enforce-gates", dest="enforce_gates", action="store_true")
    parser.add_argument("--no-enforce-gates", dest="enforce_gates", action="store_false")
    parser.set_defaults(enforce_gates=True)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--reuse-if-unchanged", dest="reuse_if_unchanged", action="store_true")
    parser.add_argument("--no-reuse", dest="reuse_if_unchanged", action="store_false")
    parser.set_defaults(reuse_if_unchanged=True)
    parser.add_argument("--only-sample", action="append", default=[])
    args = parser.parse_args()

    inventory_path = args.inventory.resolve()
    inventory = read_json(inventory_path)
    samples = inventory.get("samples", [])
    if not isinstance(samples, list) or not samples:
        raise SystemExit(f"Invalid or empty inventory: {inventory_path}")

    only = set(args.only_sample or [])
    if only:
        samples = [s for s in samples if str(s.get("sample_id", "")) in only]
        if not samples:
            raise SystemExit("--only-sample filter removed all samples.")

    parser_gate_config_path = args.parser_gate_config.resolve()
    perf_gate_config_path = args.perf_gate_config.resolve()
    contract_gate_config_path = args.contract_gate_config.resolve()
    if not parser_gate_config_path.exists():
        raise SystemExit(f"Parser gate config not found: {parser_gate_config_path}")
    if not perf_gate_config_path.exists():
        raise SystemExit(f"Performance gate config not found: {perf_gate_config_path}")
    if not contract_gate_config_path.exists():
        raise SystemExit(f"Contract compatibility config not found: {contract_gate_config_path}")
    parser_gate_config = read_json(parser_gate_config_path)
    perf_gate_config = read_json(perf_gate_config_path)

    output_root = args.output_root.resolve()
    run_dir = output_root / args.run_name
    samples_root = run_dir / "samples"
    baseline_dir = run_dir / "baseline"
    logs_root = run_dir / "logs"
    work_root = (root / "work" / "phase-b" / args.run_name).resolve()
    configured_cache = os.environ.get("DOCX_MATH_CACHE_DIR", "").strip()
    if configured_cache:
        shared_cache_dir = Path(configured_cache).expanduser().resolve()
    else:
        shared_cache_dir = (root / "work" / "phase-b" / ".cache" / "docx-html-math" / "transpect-sidecars").resolve()

    for path in (samples_root, baseline_dir, logs_root, work_root, shared_cache_dir):
        path.mkdir(parents=True, exist_ok=True)

    project_jar = args.project_jar.resolve() if args.project_jar else default_project_jar(root)
    saxon_jar = args.saxon_jar.resolve() if args.saxon_jar else default_saxon_jar(root)

    if not args.skip_build:
        build_log = logs_root / "build.log"
        need_build = args.force_build or (not project_jar.exists())
        if need_build:
            result = run_command(["mvn", "-q", "-DskipTests", "package"], root, build_log)
            if result.returncode != 0:
                raise SystemExit(f"Build failed: {build_log}")
            project_jar = default_project_jar(root)
        else:
            build_log.write_text("Build skipped by phase-b runner.\n", encoding="utf-8")

    wrapper_script = root / "scripts/transpect/run_docx_with_transpect.sh"
    qa_script = root / "scripts/qa/audit_exam_bundle.py"
    contract_script = root / "scripts/contracts/generate_output_contract.py"
    contract_check_script = root / "scripts/contracts/check_contract_compatibility.py"
    converter_file = root / "src/main/java/com/example/docxmath/DocxToHtmlConverter.java"

    results: List[Dict] = []
    category_values: Dict[str, List[float]] = {key: [] for key in CATEGORY_KEYS}

    for sample in samples:
        sample_id = str(sample.get("sample_id", "")).strip()
        subject = str(sample.get("subject", "generic")).strip()
        category = str(sample.get("category", "unknown")).strip()
        source_rel = str(sample.get("source_docx", "")).strip()
        if not sample_id or not source_rel:
            results.append(
                {
                    "sample_id": sample_id or "<missing>",
                    "status": "failed",
                    "error": "Missing sample_id or source_docx in inventory",
                }
            )
            continue

        source_docx = (root / source_rel).resolve()
        if not source_docx.exists():
            results.append(
                {
                    "sample_id": sample_id,
                    "subject": subject,
                    "category": category,
                    "source_docx": str(source_docx),
                    "status": "failed",
                    "error": "Source DOCX not found",
                }
            )
            continue

        sample_dir = samples_root / sample_id
        html_dir = sample_dir / "html"
        qa_dir = sample_dir / "qa"
        contract_dir = sample_dir / "contracts"
        sample_logs_dir = sample_dir / "logs"
        sample_work_dir = work_root / sample_id
        for path in (html_dir, qa_dir, contract_dir, sample_logs_dir, sample_work_dir):
            path.mkdir(parents=True, exist_ok=True)

        html_path = html_dir / f"{sample_id}-transpect.html"
        qa_json = qa_dir / f"{sample_id}.qa.json"
        qa_md = qa_dir / f"{sample_id}.qa.md"
        conversion_log = sample_logs_dir / "conversion.log"
        qa_log = sample_logs_dir / "qa.log"
        contract_log = sample_logs_dir / "contract.log"
        contract_gate_log = sample_logs_dir / "contract-gate.log"
        cache_meta = sample_work_dir / ".phaseb-cache.json"

        override_manifest_path = args.override_manifest.resolve() if args.override_manifest else None
        sample_override_rel = str(sample.get("override_manifest", "")).strip()
        if sample_override_rel:
            override_manifest_path = (root / sample_override_rel).resolve()
        if override_manifest_path is not None and not override_manifest_path.exists():
            results.append(
                {
                    "sample_id": sample_id,
                    "subject": subject,
                    "category": category,
                    "source_docx": str(source_docx),
                    "status": "failed",
                    "error": f"override manifest not found: {override_manifest_path}",
                }
            )
            continue

        fp = compute_fingerprint(
            source_docx=source_docx,
            subject=subject,
            output_mode=args.output_mode,
            project_jar=project_jar,
            mathtype_dir=args.mathtype_dir.resolve(),
            xmlcalabash_jar=args.xmlcalabash_jar.resolve(),
            saxon_jar=saxon_jar,
            transpect_config=args.transpect_config.resolve(),
            wrapper_script=wrapper_script,
            qa_script=qa_script,
            contract_script=contract_script,
            converter_file=converter_file,
            parser_contract_file=contract_script,
            override_manifest=override_manifest_path,
        )

        can_reuse = False
        if (
            args.reuse_if_unchanged
            and cache_meta.exists()
            and html_path.exists()
            and qa_json.exists()
            and (contract_dir / "manifest.json").exists()
            and (contract_dir / "parser_report.json").exists()
            and (contract_dir / "override_audit.json").exists()
        ):
            try:
                cached = read_json(cache_meta)
                can_reuse = cached.get("fingerprint") == fp
            except Exception:
                can_reuse = False

        conversion_seconds = 0.0
        qa_seconds = 0.0
        parser_seconds = 0.0

        if not can_reuse:
            convert_cmd = [
                str(wrapper_script),
                str(source_docx),
                str(html_path),
                str(project_jar),
                str(args.mathtype_dir.resolve()),
                str(args.xmlcalabash_jar.resolve()),
                str(saxon_jar),
                str(sample_work_dir),
                str(args.transpect_config.resolve()),
                "--subject",
                subject,
                "--output-mode",
                args.output_mode,
            ]
            env = os.environ.copy()
            env["DOCX_MATH_CACHE_DIR"] = str(shared_cache_dir)
            t0 = time.perf_counter()
            convert_result = run_command(convert_cmd, root, conversion_log, env=env)
            conversion_seconds = time.perf_counter() - t0
            if convert_result.returncode != 0:
                results.append(
                    {
                        "sample_id": sample_id,
                        "subject": subject,
                        "category": category,
                        "source_docx": str(source_docx),
                        "status": "failed",
                        "error": f"conversion failed with exit code {convert_result.returncode}",
                        "conversion_log": str(conversion_log),
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
                "--output-mode",
                args.output_mode,
                "--json-out",
                str(qa_json),
                "--md-out",
                str(qa_md),
            ]
            t1 = time.perf_counter()
            qa_result = run_command(qa_cmd, root, qa_log)
            qa_seconds = time.perf_counter() - t1
            if qa_result.returncode != 0:
                results.append(
                    {
                        "sample_id": sample_id,
                        "subject": subject,
                        "category": category,
                        "source_docx": str(source_docx),
                        "status": "failed",
                        "error": f"qa failed with exit code {qa_result.returncode}",
                        "qa_log": str(qa_log),
                    }
                )
                continue

            contract_cmd = [
                sys.executable,
                str(contract_script),
                "--html",
                str(html_path),
                "--qa-json",
                str(qa_json),
                "--source-docx",
                str(source_docx),
                "--subject",
                subject,
                "--output-mode",
                args.output_mode,
                "--out-dir",
                str(contract_dir),
            ]
            if override_manifest_path is not None:
                contract_cmd.extend(["--override-manifest", str(override_manifest_path)])
            t2 = time.perf_counter()
            contract_result = run_command(contract_cmd, root, contract_log)
            parser_seconds = time.perf_counter() - t2
            if contract_result.returncode != 0:
                results.append(
                    {
                        "sample_id": sample_id,
                        "subject": subject,
                        "category": category,
                        "source_docx": str(source_docx),
                        "status": "failed",
                        "error": f"contract generation failed with exit code {contract_result.returncode}",
                        "contract_log": str(contract_log),
                    }
                )
                continue

            cache_meta.write_text(
                json.dumps(
                    {
                        "fingerprint": fp,
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                        "html": str(html_path),
                        "qa_json": str(qa_json),
                        "contract_dir": str(contract_dir),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        else:
            qa_seconds = 0.0
            parser_seconds = 0.0

        contract_gate_summary_path = sample_logs_dir / "contract-gate-summary.json"
        contract_gate_cmd = [
            sys.executable,
            str(contract_check_script),
            "--contract-dir",
            str(contract_dir),
            "--config",
            str(contract_gate_config_path),
            "--summary-json",
            str(contract_gate_summary_path),
        ]
        contract_gate_result = run_command(contract_gate_cmd, root, contract_gate_log)
        contract_gate_summary = read_json(contract_gate_summary_path) if contract_gate_summary_path.exists() else {}
        contract_gate = {
            "passed": contract_gate_result.returncode == 0 and bool(contract_gate_summary.get("ok", False)),
            "errors": contract_gate_summary.get("errors", []),
            "warnings": contract_gate_summary.get("warnings", []),
            "summary": contract_gate_summary.get("summary", {}),
            "log_path": str(contract_gate_log),
        }
        if not contract_gate["passed"]:
            results.append(
                {
                    "sample_id": sample_id,
                    "subject": subject,
                    "category": category,
                    "source_docx": str(source_docx),
                    "status": "failed",
                    "error": "contract compatibility gate failed",
                    "contract_gate": contract_gate,
                    "contract_gate_log": str(contract_gate_log),
                }
            )
            continue

        run_tsv = parse_tsv(sample_work_dir / "run.timings.tsv")
        sidecar_tsv = parse_tsv(sample_work_dir / "timings.tsv")
        converter_ms = parse_converter_timing_ms(conversion_log)

        parser_report_path = contract_dir / "parser_report.json"
        parser_report = read_json(parser_report_path) if parser_report_path.exists() else {}
        parser_summary = parser_report.get("summary", {}) if isinstance(parser_report.get("summary", {}), dict) else {}
        parser_seconds_reported = float(parser_report.get("timings", {}).get("parser_json_build_seconds", 0.0) or 0.0)
        parser_json_build = parser_seconds_reported if parser_seconds_reported > 0 else parser_seconds
        parser_gate = evaluate_parser_gate(
            parser_summary=parser_summary,
            subject=subject,
            category=category,
            config=parser_gate_config,
        )

        unzip_load = float(sidecar_tsv.get("extract", 0.0)) + converter_ms.get("docx_load_ms", 0.0) / 1000.0
        omml_conversion = converter_ms.get("omml_handling_ms", 0.0) / 1000.0
        sidecar_generation = float(run_tsv.get("sidecar-generation", 0.0))
        image_rendering = converter_ms.get("image_rendering_ms", 0.0) / 1000.0
        cleanup_sanitize = (converter_ms.get("html_cleanup_ms", 0.0) + converter_ms.get("publish_sanitize_ms", 0.0)) / 1000.0
        write_output = converter_ms.get("html_write_ms", 0.0) / 1000.0

        timing_categories = {
            "unzip_load": round(unzip_load, 6),
            "omml_conversion": round(omml_conversion, 6),
            "sidecar_generation": round(sidecar_generation, 6),
            "image_rendering": round(image_rendering, 6),
            "cleanup_sanitize": round(cleanup_sanitize, 6),
            "parser_json_build": round(parser_json_build, 6),
            "write_output": round(write_output, 6),
        }

        for key in CATEGORY_KEYS:
            category_values[key].append(float(timing_categories.get(key, 0.0)))

        note_lines = [f"# {sample_id}", ""]
        for note in sample.get("verification_notes", []):
            note_lines.append(f"- {note}")
        note_lines.append("")
        note_path = sample_dir / "notes.md"
        note_path.write_text("\n".join(note_lines), encoding="utf-8")

        qa_payload = read_json(qa_json)
        parser_hard_failures = list(parser_gate.get("hard_failures", parser_gate.get("failures", [])) or [])
        parser_review_findings = list(parser_gate.get("review_findings", []) or [])
        sample_status = "ok"
        sample_error = ""
        if parser_hard_failures:
            sample_status = "failed_gate" if args.enforce_gates else "ok"
            sample_error = "parser quality gate failed"
        elif parser_review_findings:
            sample_status = "passed_with_review"
        sample_result = {
            "sample_id": sample_id,
            "subject": subject,
            "category": category,
            "source_docx": str(source_docx),
            "status": sample_status,
            "error": sample_error,
            "reused": can_reuse,
            "expected_artifacts": sample.get("expected_artifacts", {}),
            "artifacts": {
                "html": str(html_path),
                "qa_json": str(qa_json),
                "qa_md": str(qa_md),
                "notes": str(note_path),
                "manifest": str(contract_dir / "manifest.json"),
                "exam_bundle": str(contract_dir / "exam_bundle.json"),
                "question_bank_items": str(contract_dir / "question_bank_items.json"),
                "qa_contract": str(contract_dir / "qa.json"),
                "parser_report": str(parser_report_path),
                "override_audit": str(contract_dir / "override_audit.json"),
                "conversion_log": str(conversion_log),
                "run_timings_tsv": str(sample_work_dir / "run.timings.tsv"),
                "sidecar_timings_tsv": str(sample_work_dir / "timings.tsv"),
            },
            "timing_categories": timing_categories,
            "conversion_seconds": round(conversion_seconds, 6),
            "qa_seconds": round(qa_seconds, 6),
            "parser_seconds": round(parser_seconds, 6),
            "qa_totals": qa_payload.get("totals", {}),
            "parser_summary": parser_summary,
            "parser_warning_count": int(parser_summary.get("warning_count", 0) or 0),
            "parser_gate": parser_gate,
            "parser_gate_hard_failures": parser_hard_failures,
            "parser_gate_review_findings": parser_review_findings,
            "contract_gate": contract_gate,
            "override_manifest": str(override_manifest_path) if override_manifest_path is not None else "",
        }
        results.append(sample_result)

    ok_results = [item for item in results if item.get("status") == "ok"]
    review_results = [item for item in results if item.get("status") == "passed_with_review"]
    successful_results = [item for item in results if item.get("status") in {"ok", "passed_with_review"}]
    aggregate: Dict[str, Dict[str, float]] = {}
    for key in CATEGORY_KEYS:
        values = [float(item.get("timing_categories", {}).get(key, 0.0)) for item in successful_results]
        aggregate[key] = {
            "total_seconds": round(sum(values), 6),
            "mean_seconds": round(statistics.mean(values), 6) if values else 0.0,
            "median_seconds": round(statistics.median(values), 6) if values else 0.0,
            "p90_seconds": round(percentile(values, 0.90), 6) if values else 0.0,
        }

    parser_gate_failures: List[Dict[str, Any]] = []
    parser_gate_review_findings: List[Dict[str, Any]] = []
    contract_gate_failures: List[Dict[str, Any]] = []
    for item in results:
        parser_gate = item.get("parser_gate")
        if isinstance(parser_gate, dict) and not parser_gate.get("passed", False):
            for failure in parser_gate.get("hard_failures", parser_gate.get("failures", [])) or []:
                parser_gate_failures.append(
                    {
                        "gate": "parser_quality",
                        "scope": "sample",
                        "target": item.get("sample_id", ""),
                        "metric": str(failure),
                        "actual": "",
                        "limit": "",
                    }
                )
        if isinstance(parser_gate, dict):
            for finding in parser_gate.get("review_findings", []) or []:
                parser_gate_review_findings.append(
                    {
                        "gate": "parser_quality",
                        "scope": "sample",
                        "target": item.get("sample_id", ""),
                        "metric": str(finding),
                        "actual": "",
                        "limit": "",
                    }
                )
        contract_gate = item.get("contract_gate")
        if isinstance(contract_gate, dict) and not contract_gate.get("passed", False):
            for error in contract_gate.get("errors", []) if isinstance(contract_gate.get("errors", []), list) else []:
                contract_gate_failures.append(
                    {
                        "gate": "contract_compatibility",
                        "scope": "sample",
                        "target": item.get("sample_id", ""),
                        "metric": str(error),
                        "actual": "",
                        "limit": "",
                    }
                )

    temp_report = {
        "schema_version": "phase_b_baseline.v1",
        "run_name": args.run_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inventory_path": str(inventory_path),
        "cache_dir": str(shared_cache_dir),
        "sample_count": len(results),
        "ok_count": len(ok_results),
        "failed_count": len([item for item in results if item.get("status") == "failed_gate"]),
        "category_aggregate": aggregate,
        "samples": results,
    }
    performance_gate = evaluate_performance_gates(report=temp_report, config=perf_gate_config)
    performance_gate_failures: List[Dict[str, Any]] = []
    for failure in performance_gate.get("failures", []):
        performance_gate_failures.append(
            {
                "gate": "performance",
                "scope": failure.get("scope", ""),
                "target": failure.get("sample_id", failure.get("category", "")),
                "metric": failure.get("metric", ""),
                "actual": failure.get("actual", ""),
                "limit": failure.get("limit", ""),
            }
        )

    parser_gate_passed = len(parser_gate_failures) == 0
    contract_gate_passed = len(contract_gate_failures) == 0
    performance_gate_passed = bool(performance_gate.get("passed", False))
    gate_failures = parser_gate_failures + contract_gate_failures + performance_gate_failures

    report = {
        "schema_version": "phase_b_baseline.v1",
        "run_name": args.run_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inventory_path": str(inventory_path),
        "cache_dir": str(shared_cache_dir),
        "sample_count": len(results),
        "ok_count": len(ok_results),
        "needs_review_count": len(review_results),
        "failed_count": len([item for item in results if item.get("status") == "failed_gate"]),
        "category_aggregate": aggregate,
        "samples": results,
        "gates": {
            "enforced": bool(args.enforce_gates),
            "parser_gate_passed": parser_gate_passed,
            "contract_gate_passed": contract_gate_passed,
            "performance_gate_passed": performance_gate_passed,
            "failures": gate_failures,
            "review_findings": parser_gate_review_findings,
            "parser_gate_config": str(parser_gate_config_path),
            "performance_gate_config": str(perf_gate_config_path),
            "contract_gate_config": str(contract_gate_config_path),
        },
    }

    write_json(run_dir / "regression-sample-inventory.json", {
        "schema_version": inventory.get("schema_version", "regression_set.v1"),
        "phase": inventory.get("phase", "B"),
        "description": inventory.get("description", ""),
        "samples": samples,
    })
    write_json(baseline_dir / "performance-baseline.json", report)
    (baseline_dir / "performance-baseline.md").write_text(build_baseline_markdown(report), encoding="utf-8")

    print(run_dir)
    if args.enforce_gates:
        has_sample_failures = any(item.get("status") == "failed_gate" for item in results)
        has_gate_failures = bool(report.get("gates", {}).get("failures"))
        if has_sample_failures or has_gate_failures:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
