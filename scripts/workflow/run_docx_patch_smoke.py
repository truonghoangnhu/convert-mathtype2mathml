#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JAR = REPO_ROOT / "target" / "docx-html-math-1.0.0-jar-with-dependencies.jar"
DEFAULT_PRESET_CONFIG = REPO_ROOT / "scripts" / "workflow" / "docx_patch_smoke_presets.json"
UNRESOLVED_HELPER_PATH = Path(__file__).with_name("explain_unresolved_manifest.py")

SUMMARY_KEY_ORDER = [
    "scanned",
    "block",
    "inline",
    "native",
    "unresolved",
    "skipped_unsafe_inline",
    "skipped_multi",
    "skipped_unknown",
    "multi_patched",
    "multi_skipped_unsafe",
    "multi_skipped_ambiguous",
]

SEMANTIC_KEY_ORDER = [
    "equation_scanned",
    "equation_patched",
    "equation_native",
    "equation_handled",
    "equation_structural_residual_skips",
    "unresolved_equation_upstream",
    "unresolved_equation_other",
    "non_equation_embedded_objects",
    "suppressed_non_equation_objects",
]

SKIP_REASON_ORDER = [
    "NATIVE_OMML_PRESENT",
    "DRAWING_IN_RUN",
    "LAST_RENDERED_PAGE_BREAK_IN_RUN",
    "MULTIPLE_OBJECTS_IN_SINGLE_RUN",
    "MIXED_OBJECT_AND_TEXT_IN_RUN",
    "UNSUPPORTED_PARAGRAPH_CHILD",
    "UNKNOWN_SOURCE_KIND",
    "AMBIGUOUS_SEGMENT_SEQUENCE",
    "UNRESOLVED_MANIFEST",
    "OMML_CONVERSION_FAILED",
    "XML_MUTATION_ROLLBACK",
    "OTHER_UNSAFE_MODEL",
]

DIAGNOSTIC_ROOT_CAUSE_ORDER = [
    "NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST",
    "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "UNUSABLE_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST",
    "MANIFEST_ENTRY_POINTS_TO_MISSING_SIDECAR",
    "MANIFEST_ENTRY_POINTS_TO_UNUSABLE_SIDECAR",
    "LEAF_FALLBACK_AMBIGUOUS",
    "NO_GENERATED_BIN_SIDECAR",
    "MANIFEST_MISSING_ENTRY",
]

NON_RESIDUAL_SKIP_REASONS = {"NATIVE_OMML_PRESENT"}
NON_PATCH_CANDIDATE_SKIP_REASONS = {
    "NATIVE_OMML_PRESENT",
    "UNRESOLVED_MANIFEST",
    "OMML_CONVERSION_FAILED",
    "XML_MUTATION_ROLLBACK",
}
STRUCTURAL_PATCH_SKIP_REASONS = {
    reason
    for reason in SKIP_REASON_ORDER
    if reason not in NON_RESIDUAL_SKIP_REASONS and reason not in NON_PATCH_CANDIDATE_SKIP_REASONS
}
EQUATION_UPSTREAM_ROOT_CAUSES = {
    "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "UNUSABLE_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
    "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST",
    "MANIFEST_ENTRY_POINTS_TO_MISSING_SIDECAR",
    "MANIFEST_ENTRY_POINTS_TO_UNUSABLE_SIDECAR",
    "NO_GENERATED_BIN_SIDECAR",
}
NON_EQUATION_ROOT_CAUSES = {"NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST"}
DECISION_MIN_AFFECTED_PRESETS = 2
DECISION_MIN_TOTAL_COUNT = 3

SUMMARY_RE = re.compile(r"(\w+)=([0-9]+)")
BREAKDOWN_RE = re.compile(r"^- ([A-Z0-9_]+)=([0-9]+)$")
_UNRESOLVED_HELPER = None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DOCX patch benchmark presets and emit stable smoke/benchmark summaries.")
    parser.add_argument("--preset", action="append", default=[], help="Named smoke preset to run. Repeat for multiple presets.")
    parser.add_argument("--all-presets", action="store_true", help="Run every preset from the preset registry.")
    parser.add_argument("--subject", action="append", default=[], help="Optional subject filter (math, physics, chemistry, mixed). Repeat to allow multiple subjects.")
    parser.add_argument("--preset-config", default=str(DEFAULT_PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--list-presets", action="store_true", help="List available presets and exit.")
    parser.add_argument("--jar", default=str(DEFAULT_JAR), help="Path to built fat jar.")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "out" / "docx-patch-smoke"), help="Directory for patched DOCX outputs.")
    parser.add_argument("--patch-log-level", choices=("summary", "warnings"), default="summary", help="Patch-docx log level.")
    parser.add_argument("--format", choices=("text", "jsonl", "tsv"), default="text", help="Output format for benchmark aggregation.")
    args = parser.parse_args()

    try:
        preset_registry = load_preset_registry(Path(args.preset_config).resolve())
        if args.list_presets:
            emit_preset_list(preset_registry, normalize_subjects(args.subject))
            return 0
        selected_preset_names = select_preset_names(
            preset_registry,
            explicit_names=args.preset,
            use_all_presets=args.all_presets,
            subject_filters=normalize_subjects(args.subject),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    jar = Path(args.jar).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not jar.exists():
        print(f"Jar not found: {jar}", file=sys.stderr)
        return 2

    results = []
    failures = []
    for preset_name in selected_preset_names:
        preset = preset_registry[preset_name]
        result = run_preset(preset_name, preset, jar, out_dir, args.patch_log_level)
        results.append(result)
        if result["status"] != "ok":
            failures.append((preset_name, result["error"]))

    aggregate = aggregate_results(results)
    emit_results(results, aggregate, args.format)

    if failures:
        print("\nFailures:", file=sys.stderr)
        for preset_name, detail in failures:
            print(f"- {preset_name}: {detail}", file=sys.stderr)
        return 1
    return 0


def load_preset_registry(config_path: Path) -> dict[str, dict]:
    if not config_path.exists():
        raise FileNotFoundError(f"Preset config not found: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    presets = {}
    for raw_preset in data.get("presets", []):
        name = raw_preset["name"]
        if name in presets:
            raise ValueError(f"Duplicate preset name in config: {name}")
        presets[name] = {
            "name": name,
            "subject": raw_preset.get("subject", "unknown"),
            "input_rel": raw_preset["input"],
            "manifest_rel": raw_preset["manifest"],
            "output_name": raw_preset["output_name"],
            "input": (REPO_ROOT / raw_preset["input"]).resolve(),
            "manifest": (REPO_ROOT / raw_preset["manifest"]).resolve(),
            "workdir": (REPO_ROOT / raw_preset["manifest"]).resolve().parent,
        }
    return presets


def normalize_subjects(subjects: list[str]) -> list[str]:
    return [subject.strip().lower() for subject in subjects if subject.strip()]


def select_preset_names(
    preset_registry: dict[str, dict],
    explicit_names: list[str],
    use_all_presets: bool,
    subject_filters: list[str],
) -> list[str]:
    if explicit_names and use_all_presets:
        raise ValueError("Choose either --preset or --all-presets, not both.")
    if not explicit_names and not use_all_presets:
        raise ValueError("Choose at least one --preset or use --all-presets.")

    selected_names = []
    seen = set()
    if use_all_presets:
        candidates = list(preset_registry)
    else:
        missing = [name for name in explicit_names if name not in preset_registry]
        if missing:
            available = ", ".join(sorted(preset_registry))
            raise ValueError(f"Unknown preset(s): {', '.join(missing)}. Available presets: {available}")
        candidates = explicit_names

    for name in candidates:
        if name in seen:
            continue
        seen.add(name)
        selected_names.append(name)

    if subject_filters:
        allowed = set(subject_filters)
        selected_names = [name for name in selected_names if preset_registry[name]["subject"].lower() in allowed]
        if not selected_names:
            raise ValueError(f"No presets matched subject filter(s): {', '.join(subject_filters)}")

    return selected_names


def emit_preset_list(preset_registry: dict[str, dict], subject_filters: list[str]) -> None:
    names = select_preset_names(
        preset_registry,
        explicit_names=[],
        use_all_presets=True,
        subject_filters=subject_filters,
    )
    print("Available presets:")
    for name in names:
        preset = preset_registry[name]
        print(
            f"- {name} subject={preset['subject']} input={preset['input_rel']} manifest={preset['manifest_rel']}"
        )


def run_preset(
    preset_name: str,
    preset: dict,
    jar: Path,
    out_dir: Path,
    patch_log_level: str,
) -> dict:
    output_docx = out_dir / preset["output_name"]
    missing_paths = []
    if not preset["input"].exists():
        missing_paths.append(f"input={preset['input']}")
    if not preset["manifest"].exists():
        missing_paths.append(f"manifest={preset['manifest']}")
    if missing_paths:
        return {
            "preset": preset_name,
            "subject": preset["subject"],
            "status": "missing",
            "summary": {},
            "breakdown": {},
            "output": str(output_docx),
            "error": "missing input or manifest: " + ", ".join(missing_paths),
        }

    cmd = [
        "java",
        "-jar",
        str(jar),
        "--patch-docx",
        str(preset["input"]),
        str(output_docx),
        "--mathml-manifest",
        str(preset["manifest"]),
        "--patch-log-level",
        patch_log_level,
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    parsed = parse_patch_output(proc.stdout)
    status = "ok" if proc.returncode == 0 else f"fail({proc.returncode})"
    reporting = collect_reporting_semantics(preset, parsed)
    return {
        "preset": preset_name,
        "subject": preset["subject"],
        "status": status,
        "summary": parsed["summary"],
        "breakdown": parsed["breakdown"],
        "semantics": reporting["values"],
        "diagnostic_root_causes": reporting["diagnostic_root_causes"],
        "diagnostic_decision": reporting["diagnostic_decision"],
        "output": str(output_docx),
        "error": proc.stderr.strip() or proc.stdout.strip() or "unknown error",
    }


def parse_patch_output(stdout: str) -> dict:
    lines = stdout.splitlines()
    summary_line = next((line for line in lines if line.startswith("Patch summary: ")), "")
    summary = {}
    if summary_line:
        summary = {key: int(value) for key, value in SUMMARY_RE.findall(summary_line)}

    breakdown = {}
    in_breakdown = False
    for line in lines:
        stripped = line.strip()
        if stripped == "Skip breakdown:":
            in_breakdown = True
            continue
        if not in_breakdown:
            continue
        match = BREAKDOWN_RE.match(stripped)
        if not match:
            continue
        breakdown[match.group(1)] = int(match.group(2))
    return {"summary": summary, "breakdown": breakdown}


def aggregate_results(results: list[dict]) -> dict:
    ok_results = [result for result in results if result["status"] == "ok"]
    summary_keys = merged_keys((result["summary"] for result in ok_results), SUMMARY_KEY_ORDER)
    reason_keys = merged_keys((result["breakdown"] for result in ok_results), SKIP_REASON_ORDER)
    semantic_keys = merged_keys((result.get("semantics", {}) for result in ok_results), SEMANTIC_KEY_ORDER)
    diagnostic_root_cause_keys = merged_keys(
        (result.get("diagnostic_root_causes", {}) for result in ok_results),
        DIAGNOSTIC_ROOT_CAUSE_ORDER,
    )

    summary_totals = {
        key: sum(result["summary"].get(key, 0) for result in ok_results)
        for key in summary_keys
    }
    reason_totals = {
        key: sum(result["breakdown"].get(key, 0) for result in ok_results)
        for key in reason_keys
    }
    reason_preset_counts = {
        key: sum(1 for result in ok_results if result["breakdown"].get(key, 0) > 0)
        for key in reason_keys
    }
    semantic_totals = {
        key: sum(result.get("semantics", {}).get(key, 0) for result in ok_results)
        for key in semantic_keys
    }
    semantic_preset_counts = {
        key: sum(1 for result in ok_results if result.get("semantics", {}).get(key, 0) > 0)
        for key in semantic_keys
    }
    diagnostic_root_cause_totals = {
        key: sum(result.get("diagnostic_root_causes", {}).get(key, 0) for result in ok_results)
        for key in diagnostic_root_cause_keys
    }
    diagnostic_root_cause_preset_counts = {
        key: sum(1 for result in ok_results if result.get("diagnostic_root_causes", {}).get(key, 0) > 0)
        for key in diagnostic_root_cause_keys
    }

    residual_reasons = [
        {
            "reason": reason,
            "count": count,
            "presets_affected": reason_preset_counts[reason],
        }
        for reason, count in reason_totals.items()
        if count > 0 and reason not in NON_RESIDUAL_SKIP_REASONS
    ]
    residual_reasons.sort(key=lambda item: (-item["count"], -item["presets_affected"], item["reason"]))
    diagnostic_residuals = [
        {
            "root_cause": root_cause,
            "count": count,
            "presets_affected": diagnostic_root_cause_preset_counts[root_cause],
        }
        for root_cause, count in diagnostic_root_cause_totals.items()
        if count > 0
    ]
    diagnostic_residuals.sort(key=lambda item: (-item["count"], -item["presets_affected"], item["root_cause"]))

    decision_hint = build_decision_hint(residual_reasons, semantic_totals, diagnostic_residuals)
    presets_with_residual_skips = sum(
        1
        for result in ok_results
        if any(
            count > 0 and reason not in NON_RESIDUAL_SKIP_REASONS
            for reason, count in result["breakdown"].items()
        )
    )

    return {
        "selected_presets": [result["preset"] for result in results],
        "presets_total": len(results),
        "presets_ok": len(ok_results),
        "presets_failed": len(results) - len(ok_results),
        "presets_with_residual_skips": presets_with_residual_skips,
        "summary_totals": summary_totals,
        "reason_totals": reason_totals,
        "reason_preset_counts": reason_preset_counts,
        "semantic_totals": semantic_totals,
        "semantic_preset_counts": semantic_preset_counts,
        "diagnostic_root_cause_totals": diagnostic_root_cause_totals,
        "diagnostic_root_cause_preset_counts": diagnostic_root_cause_preset_counts,
        "top_residual_reasons": residual_reasons[:3],
        "top_diagnostic_root_causes": diagnostic_residuals[:3],
        "decision_hint": decision_hint,
    }


def build_decision_hint(
    residual_reasons: list[dict],
    semantic_totals: dict[str, int],
    diagnostic_residuals: list[dict],
) -> dict:
    if not residual_reasons:
        return {
            "level": "NO_ACTION",
            "focus": "NONE",
            "reason": "no residual skip reasons observed across selected presets",
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": [],
            "diagnostic_triggers": [],
        }

    patch_candidate_reasons = [
        reason
        for reason in residual_reasons
        if reason["reason"] not in NON_PATCH_CANDIDATE_SKIP_REASONS
    ]
    structural_residual_count = semantic_totals.get("equation_structural_residual_skips", 0)
    unresolved_equation_upstream = semantic_totals.get("unresolved_equation_upstream", 0)
    unresolved_equation_other = semantic_totals.get("unresolved_equation_other", 0)
    suppressed_non_equation_objects = semantic_totals.get("suppressed_non_equation_objects", 0)
    diagnostic_triggers = [item["root_cause"] for item in diagnostic_residuals[:3]]

    if structural_residual_count <= 0 and unresolved_equation_upstream > 0:
        return {
            "level": "INVESTIGATE",
            "focus": "EQUATION_UPSTREAM",
            "reason": (
                "no equation structural skips remain; residual equation cases come from upstream sidecar generation"
                + (
                    ", and additional residuals are suppressed non-equation objects"
                    if suppressed_non_equation_objects > 0
                    else ""
                )
            ),
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": residual_reasons[:3],
            "diagnostic_triggers": diagnostic_triggers,
        }

    if structural_residual_count <= 0 and unresolved_equation_other > 0:
        return {
            "level": "INVESTIGATE",
            "focus": "EQUATION_DIAGNOSTICS",
            "reason": "no equation structural skips remain; residual equation cases are diagnostic/corpus issues rather than patch-engine gaps",
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": residual_reasons[:3],
            "diagnostic_triggers": diagnostic_triggers,
        }

    if structural_residual_count <= 0 and suppressed_non_equation_objects > 0:
        return {
            "level": "NO_ACTION",
            "focus": "NON_EQUATION_DIAGNOSTICS",
            "reason": "no equation residuals remain; only suppressed non-equation embedded objects remain in diagnostics",
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": residual_reasons[:3],
            "diagnostic_triggers": diagnostic_triggers,
        }

    trigger_reasons = [
        reason
        for reason in patch_candidate_reasons
        if reason["presets_affected"] >= DECISION_MIN_AFFECTED_PRESETS
        or reason["count"] >= DECISION_MIN_TOTAL_COUNT
    ]
    if trigger_reasons:
        return {
            "level": "CONSIDER_PATCH",
            "focus": "PATCH_ENGINE_STRUCTURAL",
            "reason": "at least one residual skip reason crossed the benchmark threshold",
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": trigger_reasons,
            "diagnostic_triggers": diagnostic_triggers,
        }

    if not patch_candidate_reasons:
        return {
            "level": "INVESTIGATE",
            "focus": "MANIFEST_DIAGNOSTICS",
            "reason": "residual skips exist, but only in manifest/conversion reliability buckets so no new patch heuristic is justified yet",
            "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
            "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
            "trigger_reasons": residual_reasons[:3],
            "diagnostic_triggers": diagnostic_triggers,
        }

    return {
        "level": "INVESTIGATE",
        "focus": "PATCH_ENGINE_STRUCTURAL",
        "reason": "residual structural skip reasons exist but stay below the benchmark threshold",
        "min_presets_threshold": DECISION_MIN_AFFECTED_PRESETS,
        "min_total_count_threshold": DECISION_MIN_TOTAL_COUNT,
        "trigger_reasons": patch_candidate_reasons[:3],
        "diagnostic_triggers": diagnostic_triggers,
    }


def emit_results(results: list[dict], aggregate: dict, output_format: str) -> None:
    if output_format == "jsonl":
        for result in results:
            record = {"record_type": "preset", **result}
            print(json.dumps(record, ensure_ascii=True, sort_keys=True))
        print(json.dumps({"record_type": "aggregate", **aggregate}, ensure_ascii=True, sort_keys=True))
        return

    if output_format == "tsv":
        emit_tsv(results, aggregate)
        return

    emit_text(results, aggregate)


def emit_text(results: list[dict], aggregate: dict) -> None:
    for result in results:
        print(f"{result['preset']}: {result['status']}")
        summary = result["summary"]
        if summary:
            print("  Patch summary: " + " ".join(f"{key}={summary.get(key, 0)}" for key in merged_keys([summary], SUMMARY_KEY_ORDER)))
        semantics = result.get("semantics", {})
        if semantics:
            print(
                "  Reporting semantics: "
                + " ".join(
                    f"{key}={semantics.get(key, 0)}"
                    for key in merged_keys([semantics], SEMANTIC_KEY_ORDER)
                )
            )
        breakdown = result["breakdown"]
        if breakdown:
            ordered_breakdown = merged_keys([breakdown], SKIP_REASON_ORDER)
            print("  Skip breakdown:")
            for reason in ordered_breakdown:
                print(f"  - {reason}={breakdown.get(reason, 0)}")
        diagnostic_root_causes = result.get("diagnostic_root_causes", {})
        if diagnostic_root_causes:
            print("  Residual diagnostics:")
            for root_cause in merged_keys([diagnostic_root_causes], DIAGNOSTIC_ROOT_CAUSE_ORDER):
                print(f"  - {root_cause}={diagnostic_root_causes.get(root_cause, 0)}")
        print(f"  output={result['output']}")

    print("Aggregate summary:")
    print(
        "  "
        + " ".join(
            [
                f"presets_total={aggregate['presets_total']}",
                f"presets_ok={aggregate['presets_ok']}",
                f"presets_failed={aggregate['presets_failed']}",
                f"presets_with_residual_skips={aggregate['presets_with_residual_skips']}",
            ]
        )
    )
    print(
        "  Patch totals: "
        + " ".join(
            f"{key}={aggregate['summary_totals'].get(key, 0)}"
            for key in merged_keys([aggregate["summary_totals"]], SUMMARY_KEY_ORDER)
        )
    )
    print(
        "  Equation coverage: "
        + " ".join(
            f"{key}={aggregate['semantic_totals'].get(key, 0)}"
            for key in [
                "equation_scanned",
                "equation_patched",
                "equation_native",
                "equation_handled",
                "equation_structural_residual_skips",
                "unresolved_equation_upstream",
                "unresolved_equation_other",
            ]
        )
    )
    print(
        "  Embedded object diagnostics: "
        + " ".join(
            [
                f"non_equation_embedded_objects={aggregate['semantic_totals'].get('non_equation_embedded_objects', 0)}",
                f"suppressed_non_equation_objects={aggregate['semantic_totals'].get('suppressed_non_equation_objects', 0)}",
            ]
        )
    )
    print("Aggregate skip breakdown:")
    for reason in merged_keys([aggregate["reason_totals"]], SKIP_REASON_ORDER):
        print(
            f"  - {reason}={aggregate['reason_totals'].get(reason, 0)} "
            f"presets={aggregate['reason_preset_counts'].get(reason, 0)}"
        )
    print("Aggregate diagnostic root causes:")
    if not aggregate["diagnostic_root_cause_totals"]:
        print("  - none")
    else:
        for root_cause in merged_keys([aggregate["diagnostic_root_cause_totals"]], DIAGNOSTIC_ROOT_CAUSE_ORDER):
            print(
                f"  - {root_cause}={aggregate['diagnostic_root_cause_totals'].get(root_cause, 0)} "
                f"presets={aggregate['diagnostic_root_cause_preset_counts'].get(root_cause, 0)}"
            )

    print("Top residual reasons:")
    if not aggregate["top_residual_reasons"]:
        print("  - none")
    else:
        for item in aggregate["top_residual_reasons"]:
            print(
                f"  - {item['reason']} count={item['count']} presets={item['presets_affected']}"
            )
    print("Top diagnostic root causes:")
    if not aggregate["top_diagnostic_root_causes"]:
        print("  - none")
    else:
        for item in aggregate["top_diagnostic_root_causes"]:
            print(
                f"  - {item['root_cause']} count={item['count']} presets={item['presets_affected']}"
            )

    hint = aggregate["decision_hint"]
    trigger_text = (
        "none"
        if not hint["trigger_reasons"]
        else ",".join(reason["reason"] for reason in hint["trigger_reasons"])
    )
    diagnostic_trigger_text = (
        "none"
        if not hint.get("diagnostic_triggers")
        else ",".join(hint["diagnostic_triggers"])
    )
    print(
        "Decision hint: "
        f"{hint['level']} "
        f"focus={hint.get('focus', 'NONE')} "
        f"reason=\"{hint['reason']}\" "
        f"threshold_presets={hint['min_presets_threshold']} "
        f"threshold_count={hint['min_total_count_threshold']} "
        f"triggers={trigger_text} "
        f"diagnostic_triggers={diagnostic_trigger_text}"
    )


def emit_tsv(results: list[dict], aggregate: dict) -> None:
    summary_keys = merged_keys((result["summary"] for result in results), SUMMARY_KEY_ORDER)
    breakdown_keys = merged_keys((result["breakdown"] for result in results), SKIP_REASON_ORDER)
    semantic_keys = merged_keys((result.get("semantics", {}) for result in results), SEMANTIC_KEY_ORDER)

    print("# preset_results")
    preset_headers = ["preset", "subject", "status", *summary_keys, *breakdown_keys, "output"]
    print("\t".join(preset_headers))
    for result in results:
        row = [
            result["preset"],
            result["subject"],
            result["status"],
            *[str(result["summary"].get(key, 0)) for key in summary_keys],
            *[str(result["breakdown"].get(key, 0)) for key in breakdown_keys],
            result["output"],
        ]
        print("\t".join(row))

    print("# preset_semantics")
    preset_semantic_headers = ["preset", "subject", *semantic_keys]
    print("\t".join(preset_semantic_headers))
    for result in results:
        row = [
            result["preset"],
            result["subject"],
            *[str(result.get("semantics", {}).get(key, 0)) for key in semantic_keys],
        ]
        print("\t".join(row))

    print("# aggregate_summary")
    aggregate_headers = [
        "presets_total",
        "presets_ok",
        "presets_failed",
        "presets_with_residual_skips",
        *merged_keys([aggregate["summary_totals"]], SUMMARY_KEY_ORDER),
    ]
    print("\t".join(aggregate_headers))
    print(
        "\t".join(
            [
                str(aggregate["presets_total"]),
                str(aggregate["presets_ok"]),
                str(aggregate["presets_failed"]),
                str(aggregate["presets_with_residual_skips"]),
                *[
                    str(aggregate["summary_totals"].get(key, 0))
                    for key in merged_keys([aggregate["summary_totals"]], SUMMARY_KEY_ORDER)
                ],
            ]
        )
    )

    print("# aggregate_semantics")
    aggregate_semantic_headers = [
        *merged_keys([aggregate["semantic_totals"]], SEMANTIC_KEY_ORDER),
        "presets_with_equation_structural_residual_skips",
        "presets_with_unresolved_equation_upstream",
        "presets_with_unresolved_equation_other",
        "presets_with_suppressed_non_equation_objects",
    ]
    print("\t".join(aggregate_semantic_headers))
    print(
        "\t".join(
            [
                *[
                    str(aggregate["semantic_totals"].get(key, 0))
                    for key in merged_keys([aggregate["semantic_totals"]], SEMANTIC_KEY_ORDER)
                ],
                str(aggregate["semantic_preset_counts"].get("equation_structural_residual_skips", 0)),
                str(aggregate["semantic_preset_counts"].get("unresolved_equation_upstream", 0)),
                str(aggregate["semantic_preset_counts"].get("unresolved_equation_other", 0)),
                str(aggregate["semantic_preset_counts"].get("suppressed_non_equation_objects", 0)),
            ]
        )
    )

    print("# aggregate_reasons")
    print("reason\tcount\tpresets_affected")
    for reason in merged_keys([aggregate["reason_totals"]], SKIP_REASON_ORDER):
        print(
            "\t".join(
                [
                    reason,
                    str(aggregate["reason_totals"].get(reason, 0)),
                    str(aggregate["reason_preset_counts"].get(reason, 0)),
                ]
            )
        )

    print("# aggregate_diagnostic_root_causes")
    print("root_cause\tcount\tpresets_affected")
    for root_cause in merged_keys([aggregate["diagnostic_root_cause_totals"]], DIAGNOSTIC_ROOT_CAUSE_ORDER):
        print(
            "\t".join(
                [
                    root_cause,
                    str(aggregate["diagnostic_root_cause_totals"].get(root_cause, 0)),
                    str(aggregate["diagnostic_root_cause_preset_counts"].get(root_cause, 0)),
                ]
            )
        )

    print("# top_residual_reasons")
    print("rank\treason\tcount\tpresets_affected")
    if not aggregate["top_residual_reasons"]:
        print("1\tNONE\t0\t0")
    else:
        for index, item in enumerate(aggregate["top_residual_reasons"], start=1):
            print(
                "\t".join(
                    [
                        str(index),
                        item["reason"],
                        str(item["count"]),
                        str(item["presets_affected"]),
                    ]
                )
            )

    print("# top_diagnostic_root_causes")
    print("rank\troot_cause\tcount\tpresets_affected")
    if not aggregate["top_diagnostic_root_causes"]:
        print("1\tNONE\t0\t0")
    else:
        for index, item in enumerate(aggregate["top_diagnostic_root_causes"], start=1):
            print(
                "\t".join(
                    [
                        str(index),
                        item["root_cause"],
                        str(item["count"]),
                        str(item["presets_affected"]),
                    ]
                )
            )

    print("# decision_hint")
    print("level\tfocus\treason\tthreshold_presets\tthreshold_count\ttriggers\tdiagnostic_triggers")
    hint = aggregate["decision_hint"]
    trigger_text = (
        "NONE"
        if not hint["trigger_reasons"]
        else ",".join(reason["reason"] for reason in hint["trigger_reasons"])
    )
    diagnostic_trigger_text = (
        "NONE"
        if not hint.get("diagnostic_triggers")
        else ",".join(hint["diagnostic_triggers"])
    )
    print(
        "\t".join(
            [
                hint["level"],
                hint.get("focus", "NONE"),
                hint["reason"],
                str(hint["min_presets_threshold"]),
                str(hint["min_total_count_threshold"]),
                trigger_text,
                diagnostic_trigger_text,
            ]
        )
    )


def collect_reporting_semantics(preset: dict, parsed: dict) -> dict:
    summary = parsed["summary"]
    breakdown = parsed["breakdown"]
    state = load_json_if_exists(preset["workdir"] / "tmp" / "state.json")
    object_pairs = state.get("object_pairs", [])
    non_equation_embedded_objects = sum(
        1 for pair in object_pairs if is_non_equation_object_kind(pair.get("object_kind"))
    )
    equation_scanned = max(summary.get("scanned", 0) - non_equation_embedded_objects, 0)
    equation_patched = summary.get("block", 0) + summary.get("inline", 0)
    equation_native = summary.get("native", 0)
    diagnostic = collect_unresolved_diagnostics(preset, summary.get("unresolved", 0))
    values = {
        "equation_scanned": equation_scanned,
        "equation_patched": equation_patched,
        "equation_native": equation_native,
        "equation_handled": equation_patched + equation_native,
        "equation_structural_residual_skips": sum(
            breakdown.get(reason, 0) for reason in STRUCTURAL_PATCH_SKIP_REASONS
        ),
        "unresolved_equation_upstream": diagnostic["unresolved_equation_upstream"],
        "unresolved_equation_other": diagnostic["unresolved_equation_other"],
        "non_equation_embedded_objects": non_equation_embedded_objects,
        "suppressed_non_equation_objects": diagnostic["suppressed_non_equation_objects"],
    }
    return {
        "values": values,
        "diagnostic_root_causes": diagnostic["root_cause_counts"],
        "diagnostic_decision": diagnostic["decision"],
    }


def collect_unresolved_diagnostics(preset: dict, unresolved_count: int) -> dict:
    if unresolved_count <= 0:
        return {
            "root_cause_counts": {},
            "suppressed_non_equation_objects": 0,
            "unresolved_equation_upstream": 0,
            "unresolved_equation_other": 0,
            "decision": "NO_ACTION",
        }

    helper = load_unresolved_helper()
    report = helper.analyze_preset(
        {
            "name": preset["name"],
            "subject": preset["subject"],
            "input": preset["input"],
            "manifest": preset["manifest"],
            "workdir": preset["workdir"],
        }
    )
    root_cause_counts = report.get("root_cause_counts", {})
    suppressed_non_equation_objects = sum(
        root_cause_counts.get(root_cause, 0) for root_cause in NON_EQUATION_ROOT_CAUSES
    )
    unresolved_equation_upstream = sum(
        root_cause_counts.get(root_cause, 0) for root_cause in EQUATION_UPSTREAM_ROOT_CAUSES
    )
    unresolved_equation_other = sum(
        count
        for root_cause, count in root_cause_counts.items()
        if root_cause not in NON_EQUATION_ROOT_CAUSES and root_cause not in EQUATION_UPSTREAM_ROOT_CAUSES
    )
    return {
        "root_cause_counts": root_cause_counts,
        "suppressed_non_equation_objects": suppressed_non_equation_objects,
        "unresolved_equation_upstream": unresolved_equation_upstream,
        "unresolved_equation_other": unresolved_equation_other,
        "decision": report.get("decision", "NO_ACTION"),
    }


def load_unresolved_helper():
    global _UNRESOLVED_HELPER
    if _UNRESOLVED_HELPER is not None:
        return _UNRESOLVED_HELPER
    spec = importlib.util.spec_from_file_location("explain_unresolved_manifest", UNRESOLVED_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    _UNRESOLVED_HELPER = module
    return module


def load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_non_equation_object_kind(object_kind: str | None) -> bool:
    normalized = (object_kind or "").strip().lower()
    return normalized not in {"", "equation", "unknown"}


def merged_keys(dicts, preferred_order: list[str]) -> list[str]:
    ordered = []
    seen = set()
    for key in preferred_order:
        seen.add(key)
        ordered.append(key)
    extras = set()
    for data in dicts:
        extras.update(data.keys())
    for key in sorted(extras):
        if key in seen:
            continue
        ordered.append(key)
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())
