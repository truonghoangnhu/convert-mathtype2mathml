#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.generate_modern_docx_omml_output_manifest import DEFAULT_CASE_IDS, DEFAULT_JAR
from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, read_json

DEFAULT_OUTPUT = ROOT / "regression_set" / "modern_docx_omml_runtime_confidence_report.json"
DEFAULT_OUT_ROOT = ROOT / "out" / "modern-docx-omml-runtime-confidence"


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _inventory_case_index(inventory_path: Path) -> Dict[str, Dict[str, Any]]:
    inventory = read_json(inventory_path)
    cases = inventory.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("inventory cases must be a list")
    index: Dict[str, Dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        if case_id:
            index[case_id] = case
    return index


def _source_path(case: Dict[str, Any]) -> Path:
    raw = str(case.get("source_docx", "")).strip()
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / path)


def _read_single_jsonl(path: Path) -> Dict[str, Any]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(f"expected one JSONL record in {path}, found {len(lines)}")
    payload = json.loads(lines[0])
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid patch summary payload: {path}")
    return payload


def _run_patch_case(jar: Path, case_id: str, case: Dict[str, Any], output_root: Path) -> Dict[str, Any]:
    source = _source_path(case)
    if not source.exists():
        raise FileNotFoundError(f"source docx not found: {source}")

    output_docx = output_root / f"{case_id}.runtime.generated.docx"
    summary_jsonl = output_root / f"{case_id}.runtime.patch-summary.jsonl"
    output_docx.parent.mkdir(parents=True, exist_ok=True)
    if summary_jsonl.exists():
        summary_jsonl.unlink()

    cmd = [
        "java",
        "-jar",
        str(jar),
        "--patch-docx",
        str(source),
        str(output_docx),
        "--patch-log-level",
        "summary",
        "--patch-summary-jsonl",
        str(summary_jsonl),
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"patch-docx failed for {case_id}")

    summary = _read_single_jsonl(summary_jsonl)
    scanned = int(summary.get("scanned", 0) or 0)
    native = int(summary.get("native", 0) or 0)
    unresolved = int(summary.get("unresolved", 0) or 0)
    skipped_multi = int(summary.get("skipped_multi", 0) or 0)
    optimization_signal = "native_present_no_op_dominant" if scanned > 0 and native == scanned else "mixed_or_non_native_scan"

    return {
        "case_id": case_id,
        "source_docx": _repo_relative(source),
        "runtime_ms": elapsed_ms,
        "patch_summary": {
            "scanned": scanned,
            "native": native,
            "unresolved": unresolved,
            "skipped_multi": skipped_multi,
        },
        "optimization_signal": optimization_signal,
        "output_docx": _repo_relative(output_docx),
        "patch_summary_jsonl": _repo_relative(summary_jsonl),
    }


def _timing_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = [float(item["runtime_ms"]) for item in items]
    if not values:
        return {
            "count": 0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "spread_ratio_max_to_min": 0.0,
        }
    min_ms = min(values)
    max_ms = max(values)
    spread = round(max_ms / min_ms, 3) if min_ms > 0 else 0.0
    return {
        "count": len(values),
        "min_ms": round(min_ms, 3),
        "max_ms": round(max_ms, 3),
        "mean_ms": round(statistics.mean(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "spread_ratio_max_to_min": spread,
    }


def _measure_generated_output_gate() -> Dict[str, Any]:
    cmd = ["python3", "scripts/workflow/run_modern_docx_omml_generated_output_gate.py"]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    return {
        "command": " ".join(cmd),
        "runtime_ms": elapsed_ms,
        "exit_code": proc.returncode,
        "summary_line": next((line for line in proc.stdout.splitlines() if line.startswith("Summary:")), "Summary: unavailable"),
    }


def build_report(inventory_path: Path, jar: Path, output_root: Path, case_ids: List[str]) -> Dict[str, Any]:
    if not jar.exists():
        raise FileNotFoundError(f"jar not found: {jar}")

    cases_by_id = _inventory_case_index(inventory_path)
    measurements: List[Dict[str, Any]] = []
    for case_id in case_ids:
        case = cases_by_id.get(case_id)
        if not case:
            raise ValueError(f"case not found: {case_id}")
        if str(case.get("classification", "")).strip() != "supported":
            raise ValueError(f"unsupported case in runtime set: {case_id}")
        if str(case.get("status", "active")).strip() not in {"", "active"}:
            raise ValueError(f"non-active case in runtime set: {case_id}")
        measurements.append(_run_patch_case(jar, case_id, case, output_root))

    ranked = sorted(measurements, key=lambda item: float(item["runtime_ms"]))
    most_expensive = ranked[-1] if ranked else None
    cheapest = ranked[0] if ranked else None

    gate_runtime = _measure_generated_output_gate()

    native_no_op_cases = sum(1 for item in measurements if item["optimization_signal"] == "native_present_no_op_dominant")
    outlier_note = ""
    if most_expensive and cheapest:
        ratio = float(most_expensive["runtime_ms"]) / float(cheapest["runtime_ms"]) if float(cheapest["runtime_ms"]) > 0 else 0.0
        if ratio >= 2.0:
            outlier_note = (
                f"runtime spread is visible ({most_expensive['case_id']} ~{ratio:.2f}x {cheapest['case_id']}); "
                "this is acceptable for current small baseline but worth watching if spread increases"
            )

    adequate = gate_runtime["exit_code"] == 0 and len(measurements) == len(case_ids)

    return {
        "schema_version": "modern_docx_omml_runtime_confidence.v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scope": {
            "modern_docx_only": True,
            "no_behavior_redesign": True,
            "inventory": _repo_relative(inventory_path),
            "runtime_cases": case_ids,
        },
        "patch_docx_runtime": {
            "cases_measured": measurements,
            "runtime_ranking_fast_to_slow": [
                {"case_id": item["case_id"], "runtime_ms": item["runtime_ms"]}
                for item in ranked
            ],
            "summary": _timing_summary(measurements),
            "optimization_signal_summary": {
                "native_present_no_op_dominant_cases": native_no_op_cases,
                "total_cases": len(measurements),
            },
        },
        "generated_output_gate_runtime": gate_runtime,
        "notable_asymmetries": [note for note in [outlier_note] if note],
        "runtime_confidence": {
            "adequate_for_current_practical_modern_baseline": adequate,
            "judgment": (
                "runtime surface is operationally stable for the current practical modern baseline"
                if adequate
                else "runtime confidence is not yet adequate for the current practical modern baseline"
            ),
        },
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure lightweight runtime confidence for the modern DOCX + OMML baseline.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--jar", type=Path, default=DEFAULT_JAR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--case", action="append", dest="cases", default=[], help="Case IDs to measure. Defaults to active generated-output baseline set.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    case_ids = args.cases or list(DEFAULT_CASE_IDS)
    report = build_report(args.inventory.resolve(), args.jar.resolve(), args.output_root.resolve(), case_ids)
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Runtime confidence report: {out}")
    print(
        "Summary: "
        f"cases={len(report['patch_docx_runtime']['cases_measured'])} "
        f"gate_exit={report['generated_output_gate_runtime']['exit_code']} "
        f"adequate={report['runtime_confidence']['adequate_for_current_practical_modern_baseline']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
