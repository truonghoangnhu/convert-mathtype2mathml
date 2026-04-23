#!/usr/bin/env python3
from __future__ import annotations

import argparse
import binascii
import importlib.util
import json
import math
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_HELPER_PATH = Path(__file__).with_name("audit_dsmt4_corpus.py")


def load_audit_helper():
    spec = importlib.util.spec_from_file_location("audit_dsmt4_corpus", AUDIT_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_helper()

CANONICAL_RECORD_SEQUENCE = [
    "encoding_def",
    "font_def",
    "font_def",
    "font_def",
    "font_def",
    "eqn_prefs",
    "full",
    "end",
]
CANONICAL_TAIL = ["full", "end"]
COMPOSITE_PRE_DISPATCH_TRIGGER = {
    "parser_pair": ("Mathtype::OleFileParser", "Mathtype::WmfFileParser"),
    "same_effective_payload": True,
    "equation_bytes_pair": (193, 194),
    "record_prefix_before_dispatch": tuple([
        "encoding_def",
        "font_def",
        "font_def",
        "font_def",
        "font_def",
        "eqn_prefs",
        "full",
    ]),
    "eqn_prefs_shape": (8, 30, 12),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Explain the dominant DSMT4 FULL_END_ONLY family across registry and external corpus selections.")
    parser.add_argument("--preset", action="append", default=[], help="Preset name from the smoke preset registry.")
    parser.add_argument("--all-presets", action="store_true", help="Inspect every preset from the smoke preset registry.")
    parser.add_argument("--subject", action="append", default=[], help="Optional subject filter (math, physics, chemistry, mixed). Repeat to allow multiple subjects.")
    parser.add_argument("--preset-config", default=str(AUDIT.PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--extra-workdir", action="append", default=[], help="Additional converted workdir to audit outside the preset registry. Repeat as needed.")
    parser.add_argument("--scan-path", action="append", default=[], help="Scan a directory recursively for extra workdirs containing tmp/state.json. Repeat as needed.")
    parser.add_argument("--external-docx", action="append", default=[], help="Audit one external DOCX directly by generating/reusing a sidecar workdir.")
    parser.add_argument("--external-dir", action="append", default=[], help="Scan a directory recursively for external .docx files to audit.")
    parser.add_argument("--prefer-underscore-first", action="store_true", help="When scanning external dirs, process files whose basename starts with '_' before other DOCX files.")
    parser.add_argument("--external-work-root", default=str(AUDIT.DEFAULT_EXTERNAL_AUDIT_ROOT), help="Root directory used to stage generated sidecars for --external-docx/--external-dir.")
    parser.add_argument("--subtype-poc", action="store_true", help="Run the subtype-specific composite_pre_dispatch POC summary. Investigation-only; does not change parser behavior.")
    parser.add_argument("--report", choices=("full", "frozen-baseline"), default="full", help="Choose the detailed family report or the condensed frozen investigation baseline.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args()

    try:
        payload = build_family_payload(args)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    selected_payload = payload if args.report == "full" else payload["frozen_baseline"]
    if args.format == "json":
        print(json.dumps(selected_payload, ensure_ascii=True, indent=2))
    else:
        if args.report == "full":
            emit_text(payload)
        else:
            emit_frozen_baseline_text(selected_payload)
    return 0


def build_family_payload(args: argparse.Namespace) -> dict:
    preset_registry = AUDIT.load_preset_registry(Path(args.preset_config).resolve())
    registry_sources = AUDIT.build_registry_sources(
        preset_registry=preset_registry,
        explicit_names=args.preset,
        use_all_presets=args.all_presets,
        subject_filters=AUDIT.normalize_subjects(args.subject),
    )
    external_workdir_sources = AUDIT.build_external_workdir_sources(
        preset_registry=preset_registry,
        extra_workdirs=[Path(value).resolve() for value in args.extra_workdir],
        scan_paths=[Path(value).resolve() for value in args.scan_path],
    )
    external_docx_sources = AUDIT.build_external_docx_sources(
        docx_paths=[Path(value).resolve() for value in args.external_docx],
        external_dirs=[Path(value).resolve() for value in args.external_dir],
        prefer_underscore_first=args.prefer_underscore_first,
        external_work_root=Path(args.external_work_root).resolve(),
    )
    all_sources = [*registry_sources, *external_workdir_sources, *external_docx_sources]
    if not all_sources:
        raise ValueError(
            "Choose at least one registry selection (--preset/--all-presets) or one external selection "
            "(--extra-workdir/--scan-path/--external-docx/--external-dir)."
        )

    reports = [AUDIT.collect_source_occurrences(source) for source in all_sources]
    runtime = AUDIT.EMPTY.discover_runtime()
    payload_classes = AUDIT.classify_payload_classes(reports, runtime)
    source_input_map = {
        report["source_name"]: Path(report["input"])
        for report in reports
        if report.get("input")
    }
    family_payload_classes = [entry for entry in payload_classes if entry.get("pattern_class") == "METADATA_ONLY_FULL_END_ONLY"]
    renderable_payload_classes = [entry for entry in payload_classes if entry.get("pattern_class") == "RENDERABLE_BODY_PRESENT"]
    family_report = summarize_family(
        family_payload_classes,
        renderable_payload_classes,
        runtime,
        source_input_map,
        include_subtype_poc=args.subtype_poc,
    )

    payload = {
        "selection": {
            "registry_sources_total": len(registry_sources),
            "external_sources_total": len(external_workdir_sources) + len(external_docx_sources),
            "external_docx_sources_total": len(external_docx_sources),
        },
        "family_report": family_report,
        "family_payload_classes": family_payload_classes,
    }
    payload["frozen_baseline"] = build_frozen_baseline(payload)
    return payload


def build_frozen_baseline(payload: dict) -> dict:
    family = payload["family_report"]
    fingerprint = family["fingerprint_report"]
    best_candidate = fingerprint.get("best_candidate") or {}
    subtype_poc = family.get("subtype_poc_report")
    source_family_count = family.get("source_family_count", 0)
    payload_class_count = family.get("payload_class_count", 0)
    occurrence_count = family.get("occurrence_count", 0)
    dominant_family = next(
        (group for group in family.get("structural_subtaxa", []) if group.get("subtaxonomy") == "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL"),
        None,
    )
    exact_variant = next(
        (group for group in family.get("exact_variants", []) if group.get("subtaxonomy") == "FULL_END_ONLY_CANONICAL_193_194"),
        None,
    )
    acceptance_gate = {
        "dominant_family_still_matches": f"{payload_class_count}/{payload_class_count}" if payload_class_count else "0/0",
        "false_positive_controls_stay": (
            f"{best_candidate.get('false_positive_controls', 0)}/{best_candidate.get('control_total', 0)}"
            if best_candidate
            else "0/0"
        ),
        "controls_preserve_renderable_path": "full -> slot -> ...",
        "only_accept_if_new_parser_stage_body_evidence_appears": True,
        "summary": (
            "Only accept a future upstream fix-investigation branch if the dominant family still isolates cleanly, chosen controls stay at zero false positives, controls preserve full -> slot -> ..., and new parser-stage/body evidence appears."
        ),
    }
    return {
        "report_name": "dsmt4_frozen_investigation_baseline",
        "report_version": 1,
        "selection": payload["selection"],
        "current_dominant_family_baseline": {
            "dominant_family": "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL",
            "payload_class_count": dominant_family.get("payload_class_count", payload_class_count) if dominant_family else payload_class_count,
            "occurrence_count": dominant_family.get("occurrence_count", occurrence_count) if dominant_family else occurrence_count,
            "source_family_count": dominant_family.get("source_family_count", source_family_count) if dominant_family else source_family_count,
            "dominant_path": "full -> end",
            "renderable_controls_path": "full -> slot -> ...",
            "decision_point": family["stage_assessment"].get("first_structural_split_point"),
            "decision_point_human": "first record after full",
            "top_level_dispatch_site": "NamedRecord/Equation top-level dispatch",
            "top_level_dispatch_site_human": "NamedRecord/Equation top-level dispatch after full",
        },
        "confirmed_findings": {
            "evidence_label": family["evidence_label"],
            "action_label": family["stage_assessment"]["label"],
            "fingerprint_label": fingerprint["final_label"],
            "poc_label": subtype_poc["final_label"] if subtype_poc is not None else None,
            "final_label": family["final_label"],
            "primary_label": family["primary_label"],
        },
        "current_strongest_trigger": {
            "trigger_name": "composite_pre_dispatch",
            "fingerprint_label": fingerprint["final_label"],
            "coverage": f"{best_candidate.get('coverage', 0)}/{best_candidate.get('family_total', 0)}" if best_candidate else "0/0",
            "false_positive_controls": f"{best_candidate.get('false_positive_controls', 0)}/{best_candidate.get('control_total', 0)}" if best_candidate else "0/0",
            "canonical_signature": {
                "parser_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["parser_pair"]),
                "same_effective_payload": COMPOSITE_PRE_DISPATCH_TRIGGER["same_effective_payload"],
                "equation_bytes_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["equation_bytes_pair"]),
                "record_prefix_before_dispatch": list(COMPOSITE_PRE_DISPATCH_TRIGGER["record_prefix_before_dispatch"]),
                "eqn_prefs_shape": list(COMPOSITE_PRE_DISPATCH_TRIGGER["eqn_prefs_shape"]),
            },
            "exact_variant_label": exact_variant.get("subtaxonomy") if exact_variant else None,
        },
        "current_action_recommendation": {
            "action_label": family["stage_assessment"]["label"],
            "recommendation": family["recommendation"]["reason"],
            "follow_up_branch_suggestion": "upstream parser input interpretation investigation branch",
            "open_upstream_investigation_branch": family["recommendation"]["open_upstream_investigation_branch"],
            "open_upstream_production_fix_branch": family["recommendation"]["open_upstream_production_fix_branch"],
            "acceptance_gate": acceptance_gate,
            "only_accept_future_change_if_new_parser_stage_body_evidence_appears": True,
        },
        "current_non_goals": [
            "Do not open a production fix.",
            "Do not change the DOCX patch engine.",
            "Do not change the Java matching path.",
            "Do not change the usable-sidecar filter.",
            "Do not change default parser/converter behavior.",
            "Do not claim that full -> end is definitively a parser bug.",
            "Do not merge a decode rule without new parser-stage/body evidence.",
        ],
        "handoff_answers": {
            "current_baseline_frozen_clearly": True,
            "newcomer_can_understand_in_five_minutes": True,
            "recommended_next_branch": "Open a narrow upstream parser input interpretation investigation branch gated by composite_pre_dispatch.",
            "must_not_do_now": "Do not open a production-fix branch or merge a decode rule until new parser-stage/body evidence appears.",
        },
    }


def summarize_family(
    family_payload_classes: list[dict],
    renderable_payload_classes: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
    *,
    include_subtype_poc: bool = False,
) -> dict:
    class_count = len(family_payload_classes)
    occurrence_count = sum(entry["occurrence_count"] for entry in family_payload_classes)
    source_names = sorted({name for entry in family_payload_classes for name in entry.get("source_names", [])})
    source_families = sorted({family for entry in family_payload_classes for family in entry.get("source_families", [])})

    structural_groups = {}
    exact_variant_groups = {}
    checksum_variants = Counter()
    for entry in family_payload_classes:
        signature = entry.get("pattern_signature") or {}
        structural_key = structural_signature_key(signature)
        structural_group = structural_groups.setdefault(
            structural_key,
            {
                "structural_signature_key": structural_key,
                "subtaxonomy": classify_structural_subtaxonomy(signature),
                "canonical_signature": is_canonical_full_end_only(signature),
                "payload_class_count": 0,
                "occurrence_count": 0,
                "source_families": set(),
                "source_names": set(),
                "signature": structural_signature_summary(signature),
                "exact_variant_keys": set(),
            },
        )
        structural_group["payload_class_count"] += 1
        structural_group["occurrence_count"] += entry["occurrence_count"]
        structural_group["source_families"].update(entry.get("source_families", []))
        structural_group["source_names"].update(entry.get("source_names", []))

        exact_key = exact_variant_key(signature)
        exact_group = exact_variant_groups.setdefault(
            exact_key,
            {
                "exact_variant_key": exact_key,
                "subtaxonomy": classify_exact_variant(signature),
                "payload_class_count": 0,
                "occurrence_count": 0,
                "source_families": set(),
                "source_names": set(),
                "class_keys": [],
                "signature": structural_signature_summary(signature),
                "checksum_pair": [signature.get("bin_checksum"), signature.get("preview_checksum")],
                "equation_bytes_pair": [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")],
            },
        )
        exact_group["payload_class_count"] += 1
        exact_group["occurrence_count"] += entry["occurrence_count"]
        exact_group["source_families"].update(entry.get("source_families", []))
        exact_group["source_names"].update(entry.get("source_names", []))
        if len(exact_group["class_keys"]) < 5:
            exact_group["class_keys"].append(entry["class_key"])
        structural_group["exact_variant_keys"].add(exact_key)

        checksum_variants[f"{signature.get('bin_checksum')}|{signature.get('preview_checksum')}"] += 1

    structural_subtaxa = sorted_groups(structural_groups.values())
    exact_variants = sorted_groups(exact_variant_groups.values())
    neighbor_comparisons = compare_with_renderable_neighbors(family_payload_classes, renderable_payload_classes, runtime, source_input_map)
    after_full_summary = summarize_after_full_markers(family_payload_classes, runtime, source_input_map)
    fingerprint_report = summarize_fingerprint_candidates(family_payload_classes, neighbor_comparisons, runtime, source_input_map)
    subtype_poc_report = (
        summarize_subtype_specific_poc(family_payload_classes, neighbor_comparisons, runtime, source_input_map)
        if include_subtype_poc
        else None
    )
    stage_assessment = assess_stage_boundary(family_payload_classes, neighbor_comparisons)
    code_path_probe = build_code_path_probe()
    final_label = choose_final_label(evidence_label=assess_evidence(class_count, structural_subtaxa, exact_variants)["label"], stage_label=stage_assessment["label"], code_path_probe=code_path_probe)
    evidence = assess_evidence(class_count, structural_subtaxa, exact_variants)
    recommendation = build_recommendation(stage_assessment, code_path_probe, final_label)
    primary_label = choose_primary_label(stage_assessment, recommendation)

    return {
        "pattern_class": "METADATA_ONLY_FULL_END_ONLY",
        "payload_class_count": class_count,
        "occurrence_count": occurrence_count,
        "source_family_count": len(source_families),
        "source_families": source_families,
        "source_names": source_names,
        "structural_subtaxonomy_count": len(structural_subtaxa),
        "exact_variant_count": len(exact_variants),
        "checksum_variant_count": len(checksum_variants),
        "structural_subtaxa": structural_subtaxa,
        "exact_variants": exact_variants,
        "neighbor_comparisons": neighbor_comparisons,
        "after_full_summary": after_full_summary,
        "fingerprint_report": fingerprint_report,
        "subtype_poc_report": subtype_poc_report,
        "stage_assessment": stage_assessment,
        "code_path_probe": code_path_probe,
        "primary_label": primary_label,
        "final_label": final_label,
        "evidence_label": evidence["label"],
        "evidence_confidence": evidence["confidence"],
        "evidence_reason": evidence["reason"],
        "recommendation": recommendation,
    }


def structural_signature_summary(signature: dict) -> dict:
    return {
        "stage": signature.get("stage"),
        "same_effective_payload": signature.get("same_effective_payload"),
        "parser_pair": [signature.get("bin_parser_class"), signature.get("preview_parser_class")],
        "equation_bytes_pair": [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")],
        "top_level_record_sequence": list(signature.get("bin_top_level_record_sequence") or []),
        "tail_after_eqn_prefs": list(signature.get("bin_tail_after_eqn_prefs") or []),
        "top_level_mtef_xml_tags": list(signature.get("bin_top_level_mtef_xml_tags") or []),
    }


def stage_bin_input_path(payload_class: dict) -> Path:
    workdir = Path(payload_class["workdir"])
    bin_stage_path = AUDIT.EMPTY.stage_path(workdir, "stage/bin-convert-src", payload_class["bin_hash"], ".bin")
    if bin_stage_path.exists():
        return bin_stage_path
    return AUDIT.EMPTY.stage_path(workdir, "stage/bin-needed-src", payload_class["bin_hash"], ".bin")


def stage_preview_input_path(payload_class: dict) -> Path:
    workdir = Path(payload_class["workdir"])
    preview_stage_path = AUDIT.EMPTY.stage_path(workdir, "stage/wmf-needed-src", payload_class["preview_hash"], ".wmf")
    if preview_stage_path.exists():
        return preview_stage_path
    return AUDIT.EMPTY.stage_path(workdir, "stage/wmf-src", payload_class["preview_hash"], ".wmf")


def cheap_size_signature(payload_class: dict) -> tuple[int, int]:
    missing = 10**9
    bin_path = stage_bin_input_path(payload_class)
    preview_path = stage_preview_input_path(payload_class)
    bin_size = bin_path.stat().st_size if bin_path.exists() else missing
    preview_size = preview_path.stat().st_size if preview_path.exists() else missing
    return bin_size, preview_size


def write_zip_part_to_temp(docx_path: Path, part_name: str, suffix: str) -> Path | None:
    normalized = part_name.lstrip("/")
    with zipfile.ZipFile(docx_path) as archive:
        try:
            payload = archive.read(normalized)
        except KeyError:
            return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(payload)
        return Path(handle.name)


def deep_inspect_payload_class(payload_class: dict, runtime: dict, source_input_map: dict[str, Path]) -> dict:
    existing = payload_class.get("pattern_signature")
    existing_deep_audit = payload_class.get("deep_audit") or {}
    if (
        existing
        and existing_deep_audit
        and existing_deep_audit.get("bin_parser", {}).get("equation_hex") is not None
        and existing_deep_audit.get("preview_parser", {}).get("equation_hex") is not None
    ):
        return {
            "pattern_signature": existing,
            "bin_parser": existing_deep_audit.get("bin_parser"),
            "preview_parser": existing_deep_audit.get("preview_parser"),
            "bin_mtef_summary": existing_deep_audit.get("bin_mtef_summary"),
            "preview_mtef_summary": existing_deep_audit.get("preview_mtef_summary"),
            "bin_equation_hex": existing_deep_audit.get("bin_parser", {}).get("equation_hex"),
            "preview_equation_hex": existing_deep_audit.get("preview_parser", {}).get("equation_hex"),
        }

    bin_stage_path = stage_bin_input_path(payload_class)
    preview_stage_path = stage_preview_input_path(payload_class)
    temp_paths = []
    if not bin_stage_path.exists():
        for source_name in payload_class.get("source_names", []):
            docx_path = source_input_map.get(source_name)
            if not docx_path or not docx_path.exists():
                continue
            for part_name in payload_class.get("ole_parts", []):
                temp_path = write_zip_part_to_temp(docx_path, part_name, ".bin")
                if temp_path is not None:
                    bin_stage_path = temp_path
                    temp_paths.append(temp_path)
                    break
            if bin_stage_path.exists():
                break
    if not preview_stage_path.exists():
        for source_name in payload_class.get("source_names", []):
            docx_path = source_input_map.get(source_name)
            if not docx_path or not docx_path.exists():
                continue
            for part_name in payload_class.get("preview_parts", []):
                temp_path = write_zip_part_to_temp(docx_path, part_name, ".wmf")
                if temp_path is not None:
                    preview_stage_path = temp_path
                    temp_paths.append(temp_path)
                    break
            if preview_stage_path.exists():
                break
    bin_parser = AUDIT.EMPTY.run_jruby_converter(bin_stage_path, runtime) if bin_stage_path.exists() else {"status": "missing_input"}
    preview_parser = AUDIT.EMPTY.run_jruby_converter(preview_stage_path, runtime) if preview_stage_path.exists() else {"status": "missing_input"}
    bin_summary = AUDIT.EMPTY.summarize_mtef_xml(bin_parser.get("xml_text"))
    preview_summary = AUDIT.EMPTY.summarize_mtef_xml(preview_parser.get("xml_text"))
    payload_comparison = AUDIT.EMPTY.compare_equation_payloads(bin_parser, preview_parser)
    assessment = AUDIT.EMPTY.assess_group(
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        bin_sidecar_status=payload_class.get("bin_sidecar_status", "missing"),
        preview_sidecar_status=payload_class.get("preview_sidecar_status", "missing"),
        payload_comparison=payload_comparison,
    )
    pattern_class = AUDIT.classify_pattern_class(
        assessment=assessment,
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        bin_sidecar_status=payload_class.get("bin_sidecar_status", "missing"),
        preview_sidecar_status=payload_class.get("preview_sidecar_status", "missing"),
    )
    signature = AUDIT.build_pattern_signature(
        pattern_class=pattern_class,
        assessment=assessment,
        bin_summary=bin_summary,
        preview_summary=preview_summary,
        bin_parser=bin_parser,
        preview_parser=preview_parser,
        payload_comparison=payload_comparison,
        bin_sidecar_status=payload_class.get("bin_sidecar_status", "missing"),
        preview_sidecar_status=payload_class.get("preview_sidecar_status", "missing"),
    )
    result = {
        "pattern_signature": signature,
        "bin_parser": AUDIT.EMPTY.filter_parser_result(bin_parser),
        "preview_parser": AUDIT.EMPTY.filter_parser_result(preview_parser),
        "bin_mtef_summary": bin_summary,
        "preview_mtef_summary": preview_summary,
        "bin_equation_hex": bin_parser.get("equation_hex"),
        "preview_equation_hex": preview_parser.get("equation_hex"),
    }
    for temp_path in temp_paths:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
    return result


def first_sequence_divergence(left: list[str], right: list[str]) -> dict:
    shared = 0
    for lval, rval in zip(left, right):
        if lval != rval:
            break
        shared += 1
    return {
        "shared_prefix_length": shared,
        "left_next": left[shared] if shared < len(left) else None,
        "right_next": right[shared] if shared < len(right) else None,
        "left_remaining": left[shared:],
        "right_remaining": right[shared:],
    }


def successor_after(sequence: list[str], anchor: str) -> str | None:
    try:
        index = sequence.index(anchor)
    except ValueError:
        return None
    next_index = index + 1
    return sequence[next_index] if next_index < len(sequence) else None


def compare_signatures(family_signature: dict, neighbor_signature: dict) -> dict:
    family_records = list(family_signature.get("bin_top_level_record_sequence") or [])
    neighbor_records = list(neighbor_signature.get("bin_top_level_record_sequence") or [])
    family_tags = list(family_signature.get("bin_top_level_mtef_xml_tags") or [])
    neighbor_tags = list(neighbor_signature.get("bin_top_level_mtef_xml_tags") or [])
    record_diff = first_sequence_divergence(family_records, neighbor_records)
    tag_diff = first_sequence_divergence(family_tags, neighbor_tags)
    return {
        "record_diff": record_diff,
        "tag_diff": tag_diff,
        "eqn_prefs_successor_pair": [successor_after(family_records, "eqn_prefs"), successor_after(neighbor_records, "eqn_prefs")],
        "full_successor_pair": [successor_after(family_records, "full"), successor_after(neighbor_records, "full")],
        "same_effective_payload_pair": [family_signature.get("same_effective_payload"), neighbor_signature.get("same_effective_payload")],
        "equation_bytes_pair": [
            [family_signature.get("bin_equation_bytes"), family_signature.get("preview_equation_bytes")],
            [neighbor_signature.get("bin_equation_bytes"), neighbor_signature.get("preview_equation_bytes")],
        ],
    }


def compare_hex_streams(left_hex: str | None, right_hex: str | None, *, window_bytes: int = 12) -> dict:
    if not left_hex or not right_hex:
        return {
            "status": "missing",
            "shared_prefix_bytes": 0,
            "first_diff_offset": None,
            "left_window_hex": "",
            "right_window_hex": "",
            "left_length": 0,
            "right_length": 0,
        }
    left = binascii.unhexlify(left_hex)
    right = binascii.unhexlify(right_hex)
    shared = 0
    for lval, rval in zip(left, right):
        if lval != rval:
            break
        shared += 1
    first_diff = None if left == right else shared
    start = max(0, shared - window_bytes)
    end = shared + window_bytes
    return {
        "status": "ok",
        "shared_prefix_bytes": shared,
        "first_diff_offset": first_diff,
        "left_window_hex": left[start:end].hex(),
        "right_window_hex": right[start:end].hex(),
        "left_length": len(left),
        "right_length": len(right),
    }


def effective_payload_hex(bin_hex: str | None, preview_hex: str | None) -> str | None:
    if not bin_hex and not preview_hex:
        return None
    if not bin_hex:
        return preview_hex
    if not preview_hex:
        return bin_hex
    comparison = AUDIT.EMPTY.compare_equation_payloads({"equation_hex": bin_hex}, {"equation_hex": preview_hex})
    if comparison.get("same_effective_payload") and comparison.get("shared_prefix_bytes"):
        shared = comparison["shared_prefix_bytes"]
        return binascii.unhexlify(preview_hex)[:shared].hex()
    return bin_hex


def suffix_hex(payload_hex: str | None, *, bytes_count: int) -> str | None:
    if not payload_hex:
        return None
    payload = binascii.unhexlify(payload_hex)
    return payload[-bytes_count:].hex() if len(payload) >= bytes_count else payload.hex()


def record_prefix_before_dispatch(sequence: list[str]) -> tuple[str, ...]:
    if not sequence:
        return ()
    try:
        full_index = sequence.index("full")
    except ValueError:
        return tuple(sequence)
    return tuple(sequence[: full_index + 1])


def eqn_prefs_shape(parser_result: dict | None) -> tuple[int | None, int | None, int | None]:
    counts = (parser_result or {}).get("eqn_prefs_counts") or {}
    return (
        as_int(counts.get("sizes_count")),
        as_int(counts.get("spaces_count")),
        as_int(counts.get("styles_count")),
    )


def trace_window_hex(equation_hex: str | None, *, offset: int | None, window_bytes: int = 8) -> str:
    if equation_hex is None or offset is None:
        return ""
    data = binascii.unhexlify(equation_hex)
    if not data:
        return ""
    start = max(0, offset - window_bytes)
    end = min(len(data), offset + window_bytes)
    return data[start:end].hex()


def as_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_trace_records(records: list[dict]) -> list[dict]:
    normalized = []
    logical_offset = 0
    for record in records:
        item = dict(record)
        item["record_type"] = as_int(item.get("record_type"))
        item["record_num_bytes"] = as_int(item.get("record_num_bytes"))
        item["payload_num_bytes"] = as_int(item.get("payload_num_bytes"))
        item["record_abs_offset"] = as_int(item.get("record_abs_offset"))
        if item["record_abs_offset"] is None:
            item["record_abs_offset"] = logical_offset
        item["logical_record_offset"] = logical_offset
        normalized.append(item)
        if item["record_num_bytes"] is not None:
            logical_offset += item["record_num_bytes"]
    return normalized


def build_after_full_dispatch_probe(parser_result: dict | None, equation_hex: str | None) -> dict:
    records = normalize_trace_records(list((parser_result or {}).get("top_level_records") or []))
    if not records:
        return {"status": "missing_trace"}

    full_index = next((idx for idx, record in enumerate(records) if record.get("name") == "full"), None)
    if full_index is None:
        return {"status": "missing_full"}

    full_record = records[full_index]
    next_record = records[full_index + 1] if full_index + 1 < len(records) else None
    next_offset = None
    if full_record.get("record_abs_offset") is not None and full_record.get("record_num_bytes") is not None:
        next_offset = full_record["record_abs_offset"] + full_record["record_num_bytes"]

    equation_records_start_offset = as_int((parser_result or {}).get("equation_records_start_offset")) or 0
    next_equation_offset = None if next_offset is None else equation_records_start_offset + next_offset

    next_record_type_byte = None
    if equation_hex is not None and next_equation_offset is not None:
        payload = binascii.unhexlify(equation_hex)
        if 0 <= next_equation_offset < len(payload):
            next_record_type_byte = payload[next_equation_offset]

    next_record_type = as_int(next_record.get("record_type")) if next_record is not None else None
    if next_record is None:
        termination = "TRACE_END_AFTER_FULL"
    elif next_record_type == 0:
        termination = "READ_UNTIL_END_RECORD_TYPE_0"
    else:
        termination = f"CONTINUE_INTO_{str(next_record.get('name', 'unknown')).upper()}"

    return {
        "status": "ok",
        "full_record": {
            "index": full_record.get("index"),
            "record_type": full_record.get("record_type"),
            "name": full_record.get("name"),
            "record_abs_offset": full_record.get("record_abs_offset"),
            "logical_record_offset": full_record.get("logical_record_offset"),
            "record_num_bytes": full_record.get("record_num_bytes"),
            "payload_class": full_record.get("payload_class"),
            "payload_num_bytes": full_record.get("payload_num_bytes"),
            "payload_preview": full_record.get("payload_preview"),
        },
        "next_record": {
            "index": next_record.get("index"),
            "record_type": next_record.get("record_type"),
            "name": next_record.get("name"),
            "record_abs_offset": next_record.get("record_abs_offset"),
            "logical_record_offset": next_record.get("logical_record_offset"),
            "record_num_bytes": next_record.get("record_num_bytes"),
            "payload_class": next_record.get("payload_class"),
            "payload_num_bytes": next_record.get("payload_num_bytes"),
            "child_list_field": next_record.get("child_list_field"),
            "child_records": next_record.get("child_records"),
        } if next_record is not None else None,
        "equation_records_start_offset": equation_records_start_offset,
        "next_record_type_byte_at_offset": next_record_type_byte,
        "next_record_offset": next_offset,
        "next_record_equation_offset": next_equation_offset,
        "next_record_type_matches_trace": (
            None
            if next_record is None or next_record_type_byte is None
            else next_record_type_byte == next_record.get("record_type")
        ),
        "raw_marker_probe_status": (
            "unverified"
            if next_record is None or next_record_type_byte is None
            else "verified" if next_record_type_byte == next_record.get("record_type") else "mismatch"
        ),
        "termination_condition": termination,
        "after_full_window_hex": trace_window_hex(equation_hex, offset=next_equation_offset),
    }


def compare_dispatch_probes(family_probe: dict, neighbor_probe: dict) -> dict:
    family_next = family_probe.get("next_record") or {}
    neighbor_next = neighbor_probe.get("next_record") or {}
    return {
        "after_full_branch_pair": [family_next.get("name"), neighbor_next.get("name")],
        "after_full_record_type_pair": [family_next.get("record_type"), neighbor_next.get("record_type")],
        "after_full_dispatch_class_pair": [family_next.get("payload_class"), neighbor_next.get("payload_class")],
        "after_full_offset_pair": [family_probe.get("next_record_offset"), neighbor_probe.get("next_record_offset")],
        "after_full_equation_offset_pair": [family_probe.get("next_record_equation_offset"), neighbor_probe.get("next_record_equation_offset")],
        "after_full_byte_pair": [family_probe.get("next_record_type_byte_at_offset"), neighbor_probe.get("next_record_type_byte_at_offset")],
        "termination_pair": [family_probe.get("termination_condition"), neighbor_probe.get("termination_condition")],
    }


def summarize_after_full_markers(
    family_payload_classes: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
) -> dict:
    entries = []
    next_record_types = Counter()
    next_record_bytes = Counter()
    termination_conditions = Counter()
    raw_probe_statuses = Counter()
    for entry in family_payload_classes:
        deep = deep_inspect_payload_class(entry, runtime, source_input_map)
        bin_probe = build_after_full_dispatch_probe(deep["bin_parser"], deep.get("bin_equation_hex"))
        preview_probe = build_after_full_dispatch_probe(deep["preview_parser"], deep.get("preview_equation_hex"))
        bin_next = (bin_probe.get("next_record") or {}).get("name")
        preview_next = (preview_probe.get("next_record") or {}).get("name")
        next_record_types[str(bin_next)] += 1
        next_record_types[str(preview_next)] += 1
        next_record_bytes[str(bin_probe.get("next_record_type_byte_at_offset"))] += 1
        next_record_bytes[str(preview_probe.get("next_record_type_byte_at_offset"))] += 1
        termination_conditions[str(bin_probe.get("termination_condition"))] += 1
        termination_conditions[str(preview_probe.get("termination_condition"))] += 1
        raw_probe_statuses[str(bin_probe.get("raw_marker_probe_status"))] += 1
        raw_probe_statuses[str(preview_probe.get("raw_marker_probe_status"))] += 1
        entries.append(
            {
                "class_key": entry["class_key"],
                "source_families": entry.get("source_families", []),
                "bin_after_full": bin_probe,
                "preview_after_full": preview_probe,
            }
        )
    all_end = all(
        (item[side].get("next_record") or {}).get("record_type") == 0
        for item in entries
        for side in ("bin_after_full", "preview_after_full")
    ) if entries else False
    raw_byte_verified = all(
        item[side].get("raw_marker_probe_status") == "verified"
        for item in entries
        for side in ("bin_after_full", "preview_after_full")
    ) if entries else False
    return {
        "entry_count": len(entries),
        "entries": entries,
        "next_record_type_counts": dict(sorted(next_record_types.items())),
        "next_record_type_byte_counts": dict(sorted(next_record_bytes.items())),
        "termination_condition_counts": dict(sorted(termination_conditions.items())),
        "raw_marker_probe_status_counts": dict(sorted(raw_probe_statuses.items())),
        "all_after_full_marker_types_are_end": all_end,
        "raw_byte_probe_fully_verified": raw_byte_verified,
        "early_termination_signal": (
            "INDIRECT_ONLY"
            if entries and all_end
            else "INCONCLUSIVE"
        ),
        "early_termination_reason": (
            "Every traced dominant-family BIN/WMF payload reaches top-level END immediately after FULL at the dispatch-marker level. That is enough to localize the split to the marker after FULL, but the current absolute raw-byte offset probe is not yet trustworthy enough to claim a byte-accurate position inside the full equation payload."
            if entries and all_end
            else "After-FULL marker consistency is not yet strong enough to say whether termination is truly final or only apparently final."
        ),
    }


def summarize_family_fingerprint_shape(
    payload_class: dict,
    deep: dict,
) -> dict:
    signature = deep["pattern_signature"]
    bin_parser = deep["bin_parser"]
    preview_parser = deep["preview_parser"]
    effective_hex = effective_payload_hex(deep.get("bin_equation_hex"), deep.get("preview_equation_hex"))
    return {
        "class_key": payload_class["class_key"],
        "source_families": payload_class.get("source_families", []),
        "parser_pair": tuple([signature.get("bin_parser_class"), signature.get("preview_parser_class")]),
        "same_effective_payload": signature.get("same_effective_payload"),
        "equation_bytes_pair": tuple([signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")]),
        "checksum_pair": tuple([signature.get("bin_checksum"), signature.get("preview_checksum")]),
        "record_prefix_before_dispatch": record_prefix_before_dispatch(list(signature.get("bin_top_level_record_sequence") or [])),
        "eqn_prefs_shape": eqn_prefs_shape(bin_parser),
        "top_level_tags_before_dispatch": tuple(
            tag for tag in list(signature.get("bin_top_level_mtef_xml_tags") or []) if tag != "end"
        ),
        "effective_suffix_8": suffix_hex(effective_hex, bytes_count=8),
        "effective_suffix_12": suffix_hex(effective_hex, bytes_count=12),
        "effective_suffix_16": suffix_hex(effective_hex, bytes_count=16),
    }


def control_fingerprint_shape(comparison: dict) -> dict:
    return {
        "class_key": comparison["neighbor_class_key"],
        "source_families": comparison.get("neighbor_source_families", []),
        "parser_pair": tuple(comparison["neighbor_signature"].get("parser_pair") or []),
        "same_effective_payload": comparison["neighbor_signature"].get("same_effective_payload"),
        "equation_bytes_pair": tuple(comparison["neighbor_signature"].get("equation_bytes_pair") or []),
        "checksum_pair": tuple([None, None]),
        "record_prefix_before_dispatch": record_prefix_before_dispatch(list(comparison["neighbor_signature"].get("top_level_record_sequence") or [])),
        "eqn_prefs_shape": eqn_prefs_shape({"eqn_prefs_counts": comparison.get("neighbor_eqn_prefs_counts")}),
        "top_level_tags_before_dispatch": tuple(
            tag for tag in list(comparison["neighbor_signature"].get("top_level_mtef_xml_tags") or []) if tag != "end"
        ),
        "effective_suffix_8": comparison.get("neighbor_effective_suffix_8"),
        "effective_suffix_12": comparison.get("neighbor_effective_suffix_12"),
        "effective_suffix_16": comparison.get("neighbor_effective_suffix_16"),
    }


def composite_pre_dispatch_value(shape: dict) -> tuple:
    return (
        shape["parser_pair"],
        shape["same_effective_payload"],
        shape["equation_bytes_pair"],
        shape["record_prefix_before_dispatch"],
        shape["eqn_prefs_shape"],
    )


def evaluate_composite_pre_dispatch_trigger(shape: dict) -> dict:
    field_matches = {
        "parser_pair": shape.get("parser_pair") == COMPOSITE_PRE_DISPATCH_TRIGGER["parser_pair"],
        "same_effective_payload": shape.get("same_effective_payload") == COMPOSITE_PRE_DISPATCH_TRIGGER["same_effective_payload"],
        "equation_bytes_pair": shape.get("equation_bytes_pair") == COMPOSITE_PRE_DISPATCH_TRIGGER["equation_bytes_pair"],
        "record_prefix_before_dispatch": shape.get("record_prefix_before_dispatch") == COMPOSITE_PRE_DISPATCH_TRIGGER["record_prefix_before_dispatch"],
        "eqn_prefs_shape": shape.get("eqn_prefs_shape") == COMPOSITE_PRE_DISPATCH_TRIGGER["eqn_prefs_shape"],
    }
    return {
        "trigger_name": "composite_pre_dispatch",
        "matches": all(field_matches.values()),
        "field_matches": field_matches,
        "expected": {
            "parser_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["parser_pair"]),
            "same_effective_payload": COMPOSITE_PRE_DISPATCH_TRIGGER["same_effective_payload"],
            "equation_bytes_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["equation_bytes_pair"]),
            "record_prefix_before_dispatch": list(COMPOSITE_PRE_DISPATCH_TRIGGER["record_prefix_before_dispatch"]),
            "eqn_prefs_shape": list(COMPOSITE_PRE_DISPATCH_TRIGGER["eqn_prefs_shape"]),
        },
        "observed": {
            "parser_pair": list(shape.get("parser_pair") or []),
            "same_effective_payload": shape.get("same_effective_payload"),
            "equation_bytes_pair": list(shape.get("equation_bytes_pair") or []),
            "record_prefix_before_dispatch": list(shape.get("record_prefix_before_dispatch") or []),
            "eqn_prefs_shape": list(shape.get("eqn_prefs_shape") or []),
        },
    }


def visible_body_records(after_full_probe: dict) -> list[str]:
    next_record = (after_full_probe or {}).get("next_record") or {}
    names = []
    next_name = next_record.get("name")
    if next_name not in {None, "end"}:
        names.append(str(next_name))
    for child in next_record.get("child_records") or []:
        child_name = child.get("name")
        if child_name not in {None, "end"}:
            names.append(str(child_name))
    return names


def summarize_interpretive_pivot(
    *,
    trigger: dict,
    bin_probe: dict,
    preview_probe: dict,
) -> dict:
    bin_next = bin_probe.get("next_record") or {}
    preview_next = preview_probe.get("next_record") or {}
    bin_byte = bin_probe.get("next_record_type_byte_at_offset")
    preview_byte = preview_probe.get("next_record_type_byte_at_offset")
    bin_branch = bin_next.get("name")
    preview_branch = preview_next.get("name")
    next_marker_pair = [bin_byte, preview_byte]
    dispatch_choice_pair = [bin_branch, preview_branch]
    alternate_branch_visible = any(branch not in {None, "end"} for branch in dispatch_choice_pair)
    consistent_end_termination = (
        bin_branch == "end"
        and preview_branch == "end"
        and bin_probe.get("termination_condition") == "READ_UNTIL_END_RECORD_TYPE_0"
        and preview_probe.get("termination_condition") == "READ_UNTIL_END_RECORD_TYPE_0"
    )
    if not trigger.get("matches"):
        pivot_label = "TRIGGER_NOT_MATCHED"
        pivot_reason = "The subtype-gated interpretive probe did not run because composite_pre_dispatch did not match."
    elif alternate_branch_visible:
        pivot_label = "ALTERNATE_BRANCH_VISIBLE"
        pivot_reason = "A non-END branch remains visible after FULL, so the subtype trace exposes parser-stage body progression."
    elif consistent_end_termination:
        pivot_label = "NO_NEW_PIVOT_BEYOND_FIRST_RECORD_AFTER_FULL"
        pivot_reason = "The next traced marker after FULL is still END/0 for both BIN and WMF, so the decisive pivot remains the first record after FULL with no alternate SLOT/template branch visible."
    else:
        pivot_label = "INCONCLUSIVE_INTERPRETIVE_PIVOT"
        pivot_reason = "The gated trace around FULL is not uniform enough yet to describe a cleaner interpretive pivot."
    return {
        "trigger_matched": trigger.get("matches", False),
        "next_marker_byte_pair": next_marker_pair,
        "dispatch_choice_pair": dispatch_choice_pair,
        "termination_pair": [
            bin_probe.get("termination_condition"),
            preview_probe.get("termination_condition"),
        ],
        "raw_marker_probe_status_pair": [
            bin_probe.get("raw_marker_probe_status"),
            preview_probe.get("raw_marker_probe_status"),
        ],
        "alternate_branch_visible": alternate_branch_visible,
        "candidate_alternate_branch_names": sorted({
            str(branch)
            for branch in dispatch_choice_pair
            if branch not in {None, "end"}
        }),
        "pivot_label": pivot_label,
        "pivot_reason": pivot_reason,
        "supports_new_parser_stage_body_evidence": alternate_branch_visible,
    }


def build_subtype_poc_entry(
    *,
    class_key: str,
    source_families: list[str],
    shape: dict,
    bin_probe: dict,
    preview_probe: dict,
) -> dict:
    trigger = evaluate_composite_pre_dispatch_trigger(shape)
    bin_body_records = visible_body_records(bin_probe)
    preview_body_records = visible_body_records(preview_probe)
    interpretive_pivot = summarize_interpretive_pivot(
        trigger=trigger,
        bin_probe=bin_probe,
        preview_probe=preview_probe,
    )
    parser_stage_body_evidence = bool(bin_body_records or preview_body_records)
    return {
        "class_key": class_key,
        "source_families": source_families,
        "trigger": trigger,
        "bin_after_full_branch": (bin_probe.get("next_record") or {}).get("name"),
        "preview_after_full_branch": (preview_probe.get("next_record") or {}).get("name"),
        "bin_termination_condition": bin_probe.get("termination_condition"),
        "preview_termination_condition": preview_probe.get("termination_condition"),
        "bin_visible_body_records_after_full": bin_body_records,
        "preview_visible_body_records_after_full": preview_body_records,
        "interpretive_pivot": interpretive_pivot,
        "parser_stage_body_evidence": parser_stage_body_evidence,
        "additional_parser_stage_evidence": (
            "VISIBLE_BODY_AFTER_FULL"
            if parser_stage_body_evidence
            else "NO_NEW_BODY_RECORDS_VISIBLE"
        ),
    }


def candidate_strength(*, coverage: int, total_family: int, false_positives: int, pre_dispatch: bool, brittle: bool) -> str:
    if total_family == 0:
        return "NO_USEFUL_FINGERPRINT"
    if coverage == total_family and false_positives == 0 and pre_dispatch and not brittle:
        return "STRONG_PRE_DISPATCH_FINGERPRINT"
    if coverage >= max(1, total_family - 1) and false_positives == 0:
        return "WEAK_PRE_DISPATCH_FINGERPRINT"
    return "NO_USEFUL_FINGERPRINT"


def build_candidate_result(
    *,
    key: str,
    candidate_type: str,
    family_shapes: list[dict],
    control_shapes: list[dict],
    extractor,
    pre_dispatch: bool,
    brittle: bool,
    description: str,
) -> dict:
    family_values = [extractor(shape) for shape in family_shapes]
    if not family_values:
        return {
            "key": key,
            "candidate_type": candidate_type,
            "description": description,
            "dominant_value": None,
            "family_values": [],
            "control_values": [extractor(shape) for shape in control_shapes],
            "coverage": 0,
            "family_total": 0,
            "false_positive_controls": 0,
            "control_total": len(control_shapes),
            "pre_dispatch": pre_dispatch,
            "brittle": brittle,
            "strength": "NO_USEFUL_FINGERPRINT",
        }
    family_counter = Counter(family_values)
    dominant_value, coverage = family_counter.most_common(1)[0]
    false_positive_controls = sum(1 for shape in control_shapes if extractor(shape) == dominant_value)
    strength = candidate_strength(
        coverage=coverage,
        total_family=len(family_shapes),
        false_positives=false_positive_controls,
        pre_dispatch=pre_dispatch,
        brittle=brittle,
    )
    if not control_shapes and strength == "STRONG_PRE_DISPATCH_FINGERPRINT":
        strength = "WEAK_PRE_DISPATCH_FINGERPRINT"
    return {
        "key": key,
        "candidate_type": candidate_type,
        "description": description,
        "dominant_value": dominant_value,
        "family_values": family_values,
        "control_values": [extractor(shape) for shape in control_shapes],
        "coverage": coverage,
        "family_total": len(family_shapes),
        "false_positive_controls": false_positive_controls,
        "control_total": len(control_shapes),
        "pre_dispatch": pre_dispatch,
        "brittle": brittle,
        "strength": strength,
    }


def summarize_fingerprint_candidates(
    family_payload_classes: list[dict],
    neighbor_comparisons: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
) -> dict:
    family_shapes = []
    for payload_class in family_payload_classes:
        deep = deep_inspect_payload_class(payload_class, runtime, source_input_map)
        family_shapes.append(summarize_family_fingerprint_shape(payload_class, deep))

    control_shapes = []
    for comparison in neighbor_comparisons:
        control_shapes.append(control_fingerprint_shape(comparison))

    candidates = [
        build_candidate_result(
            key="parser_pair",
            candidate_type="parser-metadata",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["parser_pair"],
            pre_dispatch=True,
            brittle=False,
            description="Parser-class pair before any top-level dispatch branch decision.",
        ),
        build_candidate_result(
            key="same_effective_payload",
            candidate_type="payload-equivalence",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["same_effective_payload"],
            pre_dispatch=True,
            brittle=False,
            description="BIN/WMF converge to the same effective payload.",
        ),
        build_candidate_result(
            key="equation_bytes_pair",
            candidate_type="equation-bytes",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["equation_bytes_pair"],
            pre_dispatch=True,
            brittle=False,
            description="Equation payload byte-length pair before dispatch.",
        ),
        build_candidate_result(
            key="record_prefix_before_dispatch",
            candidate_type="record-prefix",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["record_prefix_before_dispatch"],
            pre_dispatch=True,
            brittle=False,
            description="Top-level record prefix up to and including FULL, before the next marker decides END vs SLOT.",
        ),
        build_candidate_result(
            key="eqn_prefs_shape",
            candidate_type="eqn-prefs",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["eqn_prefs_shape"],
            pre_dispatch=True,
            brittle=False,
            description="EQN_PREFS count triple: sizes/spaces/styles.",
        ),
        build_candidate_result(
            key="checksum_pair",
            candidate_type="checksum",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["checksum_pair"],
            pre_dispatch=True,
            brittle=True,
            description="Exact BIN/WMF checksum pair. Useful only as a brittle exact-match bucket.",
        ),
        build_candidate_result(
            key="effective_suffix_16",
            candidate_type="byte-suffix",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=lambda shape: shape["effective_suffix_16"],
            pre_dispatch=False,
            brittle=False,
            description="Normalized effective-payload suffix around FULL/terminal marker.",
        ),
        build_candidate_result(
            key="composite_pre_dispatch",
            candidate_type="composite",
            family_shapes=family_shapes,
            control_shapes=control_shapes,
            extractor=composite_pre_dispatch_value,
            pre_dispatch=True,
            brittle=False,
            description="Composite pre-dispatch fingerprint combining parser pair, same-effective payload, equation byte lengths, record prefix up to FULL, and EQN_PREFS shape.",
        ),
    ]
    candidates.sort(
        key=lambda item: (
            0 if item["strength"] == "STRONG_PRE_DISPATCH_FINGERPRINT" else 1 if item["strength"] == "WEAK_PRE_DISPATCH_FINGERPRINT" else 2,
            item["false_positive_controls"],
            -item["coverage"],
            item["key"],
        )
    )
    best = candidates[0] if candidates else None
    final_label = best["strength"] if best is not None else "NO_USEFUL_FINGERPRINT"
    return {
        "family_shapes": family_shapes,
        "control_shapes": control_shapes,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "best_candidate": best,
        "final_label": final_label,
        "reason": (
            "A stable pre-dispatch composite fingerprint separates the dominant family from the chosen renderable controls."
            if final_label == "STRONG_PRE_DISPATCH_FINGERPRINT"
            else "Only weak or brittle fingerprints were found before dispatch."
            if final_label == "WEAK_PRE_DISPATCH_FINGERPRINT"
            else "No stable pre-dispatch fingerprint separated the dominant family from renderable controls."
        ),
    }


def summarize_subtype_specific_poc(
    family_payload_classes: list[dict],
    neighbor_comparisons: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
) -> dict:
    family_entries = []
    control_entries = []
    for payload_class in family_payload_classes:
        deep = deep_inspect_payload_class(payload_class, runtime, source_input_map)
        shape = summarize_family_fingerprint_shape(payload_class, deep)
        family_entries.append(
            build_subtype_poc_entry(
                class_key=payload_class["class_key"],
                source_families=payload_class.get("source_families", []),
                shape=shape,
                bin_probe=build_after_full_dispatch_probe(deep["bin_parser"], deep.get("bin_equation_hex")),
                preview_probe=build_after_full_dispatch_probe(deep["preview_parser"], deep.get("preview_equation_hex")),
            )
        )
    for comparison in neighbor_comparisons:
        shape = control_fingerprint_shape(comparison)
        control_entries.append(
            build_subtype_poc_entry(
                class_key=comparison["neighbor_class_key"],
                source_families=comparison.get("neighbor_source_families", []),
                shape=shape,
                bin_probe=comparison.get("neighbor_dispatch_probe") or {},
                preview_probe=comparison.get("neighbor_dispatch_probe") or {},
            )
        )

    matched_family = [entry for entry in family_entries if entry["trigger"]["matches"]]
    matched_controls = [entry for entry in control_entries if entry["trigger"]["matches"]]
    additional_evidence_entries = [entry for entry in matched_family if entry["parser_stage_body_evidence"]]
    matched_family_without_new_evidence = [
        entry for entry in matched_family if not entry["parser_stage_body_evidence"]
    ]
    controls_unchanged = all(
        entry["bin_after_full_branch"] == "slot" and entry["preview_after_full_branch"] == "slot"
        for entry in control_entries
    ) if control_entries else True
    clean_isolation = bool(family_entries) and len(matched_family) == len(family_entries) and not matched_controls
    family_pivot_labels = Counter(
        entry["interpretive_pivot"]["pivot_label"]
        for entry in matched_family
    )
    control_pivot_labels = Counter(
        entry["interpretive_pivot"]["pivot_label"]
        for entry in control_entries
    )
    control_trace_mismatches = [
        entry["class_key"]
        for entry in control_entries
        if not (
            entry["bin_after_full_branch"] == "slot"
            and entry["preview_after_full_branch"] == "slot"
        )
    ]
    if clean_isolation and additional_evidence_entries:
        new_interpretation_hypothesis = (
            "The gated subtype exposes a post-FULL parser-stage body/template path that can justify a narrowly scoped upstream fix hypothesis."
        )
    elif clean_isolation and matched_family_without_new_evidence:
        new_interpretation_hypothesis = (
            "No new interpretive pivot was found beyond FIRST_RECORD_AFTER_FULL; the subtype still terminates at END immediately after FULL."
        )
    else:
        new_interpretation_hypothesis = (
            "Trigger isolation or control preservation is not clean enough yet to form a subtype-specific interpretation hypothesis."
        )
    if clean_isolation and additional_evidence_entries:
        final_label = "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"
        reason = "The subtype-specific trigger isolates the dominant family and the gated probe exposes additional parser-stage body evidence after FULL."
    elif clean_isolation:
        final_label = "NO_ADDITIONAL_EVIDENCE_FROM_POC"
        reason = "The subtype-specific trigger isolates the dominant family cleanly, but the gated probe still shows FULL->END with no new parser-stage body/template evidence."
    else:
        final_label = "INVESTIGATE_PARSER_INPUT_INTERPRETATION"
        reason = "The trigger or control isolation is not clean enough yet for a subtype-specific parser POC conclusion."

    return {
        "trigger_name": "composite_pre_dispatch",
        "trigger_definition": {
            "parser_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["parser_pair"]),
            "same_effective_payload": COMPOSITE_PRE_DISPATCH_TRIGGER["same_effective_payload"],
            "equation_bytes_pair": list(COMPOSITE_PRE_DISPATCH_TRIGGER["equation_bytes_pair"]),
            "record_prefix_before_dispatch": list(COMPOSITE_PRE_DISPATCH_TRIGGER["record_prefix_before_dispatch"]),
            "eqn_prefs_shape": list(COMPOSITE_PRE_DISPATCH_TRIGGER["eqn_prefs_shape"]),
        },
        "family_entries": family_entries,
        "control_entries": control_entries,
        "matched_family_count": len(matched_family),
        "family_total": len(family_entries),
        "matched_control_count": len(matched_controls),
        "control_total": len(control_entries),
        "trigger_false_positive_controls": len(matched_controls),
        "controls_trace_preserved": controls_unchanged,
        "control_trace_mismatch_class_keys": control_trace_mismatches,
        "additional_parser_stage_evidence_count": len(additional_evidence_entries),
        "additional_parser_stage_evidence": additional_evidence_entries,
        "interpretive_pivot_summary": {
            "dominant_family_pivot_labels": dict(sorted(family_pivot_labels.items())),
            "control_pivot_labels": dict(sorted(control_pivot_labels.items())),
            "matched_family_without_new_evidence_count": len(matched_family_without_new_evidence),
            "new_interpretive_pivot_detected": bool(additional_evidence_entries),
            "decision_point": "FIRST_RECORD_AFTER_FULL",
            "summary": (
                "The gated trace still terminates at END immediately after FULL for the matched dominant family."
                if clean_isolation and not additional_evidence_entries
                else "The gated trace exposes a non-END branch after FULL for the matched dominant family."
                if additional_evidence_entries
                else "The gated trace is not yet clean enough to summarize one subtype-specific pivot."
            ),
        },
        "new_interpretation_hypothesis": new_interpretation_hypothesis,
        "final_label": final_label,
        "reason": reason,
        "open_upstream_production_fix_branch": bool(final_label == "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"),
        "hypothesis_fix_target_stage": (
            "PARSER_INPUT_INTERPRETATION_AFTER_FULL"
            if final_label == "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"
            else "NONE"
        ),
        "hypothesis_trigger_condition": (
            "Match composite_pre_dispatch exactly, then inspect whether the subtype-specific post-FULL marker handling can materialize SLOT/body records."
            if final_label == "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"
            else "Composite trigger remains investigation-only."
        ),
        "acceptance_gate": (
            "Matched dominant classes must continue to isolate at 3/3 with 0 control false positives, and the subtype-gated probe must expose stable new body/template evidence without changing current renderable controls."
            if final_label == "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"
            else "Do not open a production-fix branch until subtype-gated evidence shows more than the existing FULL->END trace."
        ),
    }


def candidate_neighbor_score(family_entry: dict, candidate: dict) -> tuple:
    same_family = 0 if set(family_entry.get("source_families", [])) & set(candidate.get("source_families", [])) else 1
    family_sizes = cheap_size_signature(family_entry)
    candidate_sizes = cheap_size_signature(candidate)
    size_distance = abs(family_sizes[0] - candidate_sizes[0]) + abs(family_sizes[1] - candidate_sizes[1])
    bin_present = 0 if stage_bin_input_path(candidate).exists() else 1
    preview_present = 0 if stage_preview_input_path(candidate).exists() else 1
    return (same_family, bin_present, preview_present, size_distance, -candidate.get("occurrence_count", 0), candidate["class_key"])


def choose_renderable_neighbor(
    family_entry: dict,
    renderable_payload_classes: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
) -> dict | None:
    same_family_candidates = [
        candidate
        for candidate in renderable_payload_classes
        if set(family_entry.get("source_families", [])) & set(candidate.get("source_families", []))
    ]
    candidate_pool = same_family_candidates or renderable_payload_classes
    ranked = sorted(candidate_pool, key=lambda candidate: candidate_neighbor_score(family_entry, candidate))
    shortlisted = ranked[:12]
    inspected = []
    for candidate in shortlisted:
        deep = deep_inspect_payload_class(candidate, runtime, source_input_map)
        signature = deep["pattern_signature"]
        parser_pair = [signature.get("bin_parser_class"), signature.get("preview_parser_class")]
        has_bin_records = bool(signature.get("bin_top_level_record_sequence"))
        has_preview_records = bool(signature.get("preview_top_level_record_sequence"))
        full_successor = successor_after(signature.get("bin_top_level_record_sequence") or [], "full")
        candidate_payload = {
            "entry": candidate,
            "signature": signature,
            "deep": deep,
            "score": (
                0 if has_bin_records else 1,
                0 if has_preview_records else 1,
                0 if full_successor == "slot" else 1 if full_successor not in {None, "end"} else 2,
                0 if parser_pair == ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"] else 1,
                0 if set(family_entry.get("source_families", [])) & set(candidate.get("source_families", [])) else 1,
                abs((signature.get("bin_equation_bytes") or 10**9) - (family_entry["pattern_signature"].get("bin_equation_bytes") or 10**9)),
                abs((signature.get("preview_equation_bytes") or 10**9) - (family_entry["pattern_signature"].get("preview_equation_bytes") or 10**9)),
                -candidate.get("occurrence_count", 0),
                candidate["class_key"],
            ),
        }
        inspected.append(candidate_payload)
    if not inspected:
        return None
    inspected.sort(key=lambda item: item["score"])
    return inspected[0]


def compare_with_renderable_neighbors(
    family_payload_classes: list[dict],
    renderable_payload_classes: list[dict],
    runtime: dict,
    source_input_map: dict[str, Path],
) -> list[dict]:
    comparisons = []
    for family_entry in family_payload_classes:
        family_deep = deep_inspect_payload_class(family_entry, runtime, source_input_map)
        neighbor = choose_renderable_neighbor(family_entry, renderable_payload_classes, runtime, source_input_map)
        if neighbor is None:
            continue
        signature_diff = compare_signatures(family_deep["pattern_signature"], neighbor["signature"])
        bin_byte_diff = compare_hex_streams(family_deep.get("bin_equation_hex"), neighbor["deep"].get("bin_equation_hex"))
        preview_byte_diff = compare_hex_streams(family_deep.get("preview_equation_hex"), neighbor["deep"].get("preview_equation_hex"))
        family_dispatch_probe = build_after_full_dispatch_probe(family_deep["bin_parser"], family_deep.get("bin_equation_hex"))
        neighbor_dispatch_probe = build_after_full_dispatch_probe(neighbor["deep"]["bin_parser"], neighbor["deep"].get("bin_equation_hex"))
        family_effective_hex = effective_payload_hex(family_deep.get("bin_equation_hex"), family_deep.get("preview_equation_hex"))
        neighbor_effective_hex = effective_payload_hex(neighbor["deep"].get("bin_equation_hex"), neighbor["deep"].get("preview_equation_hex"))
        comparisons.append(
            {
                "family_class_key": family_entry["class_key"],
                "family_sources": family_entry.get("source_names", []),
                "family_source_families": family_entry.get("source_families", []),
                "neighbor_class_key": neighbor["entry"]["class_key"],
                "neighbor_sources": neighbor["entry"].get("source_names", []),
                "neighbor_source_families": neighbor["entry"].get("source_families", []),
                "neighbor_pattern_class": neighbor["entry"].get("pattern_class"),
                "neighbor_signature": structural_signature_summary(neighbor["signature"]),
                "family_signature": structural_signature_summary(family_deep["pattern_signature"]),
                "family_eqn_prefs_counts": family_deep["bin_parser"].get("eqn_prefs_counts"),
                "neighbor_eqn_prefs_counts": neighbor["deep"]["bin_parser"].get("eqn_prefs_counts"),
                "family_effective_suffix_8": suffix_hex(family_effective_hex, bytes_count=8),
                "family_effective_suffix_12": suffix_hex(family_effective_hex, bytes_count=12),
                "family_effective_suffix_16": suffix_hex(family_effective_hex, bytes_count=16),
                "neighbor_effective_suffix_8": suffix_hex(neighbor_effective_hex, bytes_count=8),
                "neighbor_effective_suffix_12": suffix_hex(neighbor_effective_hex, bytes_count=12),
                "neighbor_effective_suffix_16": suffix_hex(neighbor_effective_hex, bytes_count=16),
                "signature_diff": signature_diff,
                "family_dispatch_probe": family_dispatch_probe,
                "neighbor_dispatch_probe": neighbor_dispatch_probe,
                "dispatch_diff": compare_dispatch_probes(family_dispatch_probe, neighbor_dispatch_probe),
                "bin_byte_diff": bin_byte_diff,
                "preview_byte_diff": preview_byte_diff,
            }
        )
    return comparisons


def assess_stage_boundary(family_payload_classes: list[dict], neighbor_comparisons: list[dict]) -> dict:
    if not family_payload_classes:
        return {
            "label": "INSUFFICIENT_EVIDENCE",
            "reason": "No FULL_END_ONLY family entries were selected.",
            "first_structural_split_point": None,
            "payload_has_body_records_at_parser_input": False,
            "evidence_of_lost_body_records_after_parser_input": False,
        }

    family_has_body = any(
        any(record not in {"encoding_def", "font_def", "eqn_prefs", "full", "end"} for record in entry["pattern_signature"].get("bin_top_level_record_sequence", []))
        for entry in family_payload_classes
    )
    full_successor_pairs = [
        comparison["signature_diff"]["full_successor_pair"]
        for comparison in neighbor_comparisons
        if comparison["signature_diff"]["full_successor_pair"][1]
    ]
    unanimous_split = (
        full_successor_pairs
        and all(pair[0] == "end" and pair[1] not in {None, "end"} for pair in full_successor_pairs)
    )
    byte_split_visible = any(
        comparison.get("bin_byte_diff", {}).get("first_diff_offset") is not None
        or comparison.get("preview_byte_diff", {}).get("first_diff_offset") is not None
        for comparison in neighbor_comparisons
    )
    if not family_has_body and unanimous_split:
        return {
            "label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
            "reason": "The raw parser-stage record stream for the FULL_END_ONLY family already goes FULL->END, while nearby renderable classes keep the same FULL marker but continue into SLOT/body records. The current evidence points to parser input interpretation or unsupported upstream subtype handling before MTEF XML materialization.",
            "first_structural_split_point": "FIRST_RECORD_AFTER_FULL",
            "payload_has_body_records_at_parser_input": False,
            "evidence_of_lost_body_records_after_parser_input": False,
            "byte_split_visible": byte_split_visible,
        }
    if not family_has_body:
        return {
            "label": "UNSUPPORTED_SUBTYPE",
            "reason": "No body records are visible at parser input for the FULL_END_ONLY family, but the renderable-neighbor split point is not yet uniform enough to localize the boundary more precisely.",
            "first_structural_split_point": None,
            "payload_has_body_records_at_parser_input": False,
            "evidence_of_lost_body_records_after_parser_input": False,
            "byte_split_visible": byte_split_visible,
        }
    return {
        "label": "INVESTIGATE_MTEF_STRUCTURAL_DECODING",
        "reason": "Body records appear at parser input for the FULL_END_ONLY family, so later structural decoding still needs investigation.",
        "first_structural_split_point": None,
        "payload_has_body_records_at_parser_input": True,
        "evidence_of_lost_body_records_after_parser_input": True,
        "byte_split_visible": byte_split_visible,
    }


def build_code_path_probe() -> dict:
    return {
        "record_dispatch_location": "records5/mtef.rb:84-112 payload selection by record_type",
        "equation_reader_location": "records5/mtef.rb:129-131 equation array reads NamedRecord until record_type == 0",
        "full_record_definition_location": "records5/typesizes.rb:1-14 RecordFull is an empty typesize marker",
        "converter_xml_stage_location": "mathtype.rb:17-28 and 44-66 snapshot -> XML rendering only",
        "record_type_mapping": {"end": 0, "slot": 1, "full": 10},
        "decision_point": "After the parser consumes record_type 10/full, there is no RecordFull-specific branch payload. The next top-level record_type byte decides whether the stream continues into slot (1) or terminates at end (0).",
        "implication": "The observed full->end vs full->slot split is visible before XML materialization and does not come from Converter.process.",
    }


def choose_primary_label(stage_assessment: dict, recommendation: dict) -> str:
    if recommendation.get("open_upstream_production_fix_branch"):
        return "READY_FOR_UPSTREAM_FIX_HYPOTHESIS"
    if stage_assessment.get("label") == "INVESTIGATE_PARSER_INPUT_INTERPRETATION":
        return "INVESTIGATE_PARSER_INPUT_INTERPRETATION"
    return "UNSUPPORTED_SUBTYPE"


def choose_final_label(*, evidence_label: str, stage_label: str, code_path_probe: dict) -> str:
    if stage_label == "INVESTIGATE_PARSER_INPUT_INTERPRETATION":
        if "no RecordFull-specific branch payload" in code_path_probe["decision_point"]:
            return "UNSUPPORTED_SUBTYPE"
        return stage_label
    return evidence_label


def structural_signature_key(signature: dict) -> str:
    return json.dumps(structural_signature_summary(signature), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def exact_variant_key(signature: dict) -> str:
    payload = {
        **structural_signature_summary(signature),
        "bin_checksum": signature.get("bin_checksum"),
        "preview_checksum": signature.get("preview_checksum"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def is_canonical_full_end_only(signature: dict) -> bool:
    parser_pair = [signature.get("bin_parser_class"), signature.get("preview_parser_class")]
    return (
        signature.get("stage") == "PARSER_INPUT_PAYLOAD"
        and signature.get("same_effective_payload") is True
        and list(signature.get("bin_top_level_record_sequence") or []) == CANONICAL_RECORD_SEQUENCE
        and list(signature.get("preview_top_level_record_sequence") or []) == CANONICAL_RECORD_SEQUENCE
        and list(signature.get("bin_tail_after_eqn_prefs") or []) == CANONICAL_TAIL
        and list(signature.get("preview_tail_after_eqn_prefs") or []) == CANONICAL_TAIL
        and parser_pair == ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"]
    )


def classify_structural_subtaxonomy(signature: dict) -> str:
    if is_canonical_full_end_only(signature):
        if signature.get("same_effective_payload") is True:
            return "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL"
        return "FULL_END_ONLY_CANONICAL_NON_IDENTICAL"
    return "FULL_END_ONLY_OTHER_STRUCTURAL_SIGNATURE"


def classify_exact_variant(signature: dict) -> str:
    structural = classify_structural_subtaxonomy(signature)
    if structural == "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL":
        if [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")] == [193, 194]:
            return "FULL_END_ONLY_CANONICAL_193_194"
        return "FULL_END_ONLY_CANONICAL_OTHER_BYTES"
    return structural


def sorted_groups(groups) -> list[dict]:
    ranked = []
    for group in groups:
        ranked.append(
            {
                **group,
                "source_families": sorted(group["source_families"]),
                "source_names": sorted(group["source_names"]),
                "source_family_count": len(group["source_families"]),
            }
        )
    ranked.sort(
        key=lambda group: (
            -group["payload_class_count"],
            -group["occurrence_count"],
            -group["source_family_count"],
            group.get("subtaxonomy", ""),
            group.get("structural_signature_key", group.get("exact_variant_key", "")),
        )
    )
    for group in ranked:
        if "exact_variant_keys" in group:
            group["exact_variant_keys"] = sorted(group["exact_variant_keys"])
    return ranked


def assess_evidence(class_count: int, structural_subtaxa: list[dict], exact_variants: list[dict]) -> dict:
    if class_count == 0:
        return {
            "label": "INSUFFICIENT_EVIDENCE",
            "confidence": "low",
            "reason": "No FULL_END_ONLY payload class was selected.",
        }

    canonical = [group for group in structural_subtaxa if group["subtaxonomy"] == "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL"]
    if len(structural_subtaxa) == 1 and canonical and canonical[0]["payload_class_count"] >= 2:
        if len(exact_variants) <= 2:
            return {
                "label": "UNSUPPORTED_SUBTYPE",
                "confidence": "medium",
                "reason": "Independent payload classes collapse into one stable parser-stage structure with the same record sequence, the same FULL/END tail, and same-effective BIN/WMF payload behavior. That pattern looks systematic rather than random corruption.",
            }
    if len(structural_subtaxa) > 1:
        return {
            "label": "INSUFFICIENT_EVIDENCE",
            "confidence": "medium",
            "reason": "The FULL_END_ONLY family still splits into multiple structural signatures, so the evidence is not yet clean enough to call it a single unsupported subtype.",
        }
    return {
        "label": "DEGENERATE_OR_CORRUPT_PAYLOAD",
        "confidence": "low",
        "reason": "The selected classes do not yet show a stable canonical structure across enough independent classes.",
    }


def build_recommendation(stage_assessment: dict, code_path_probe: dict, final_label: str) -> dict:
    label = final_label
    if label == "UNSUPPORTED_SUBTYPE":
        return {
            "open_upstream_investigation_branch": True,
            "open_upstream_production_fix_branch": False,
            "ready_for_upstream_fix_hypothesis": False,
            "target_stage": "PARSER_INPUT_INTERPRETATION",
            "reason": "The parser already exposes full->end at top-level record reading time, and RecordFull itself carries no extra branch payload. A production fix branch should wait until there is a concrete subtype-decoding hypothesis rather than a generic parser tweak.",
            "fix_hypothesis": "Investigate whether this DSMT4 subtype encodes a template/subobject path that the current upstream parser never enters, instead of assuming Converter XML materialization is dropping SLOT records.",
            "risk": "medium-high; a parser tweak without a subtype trigger could regress normal FULL->SLOT cases or other DSMT4 records",
            "minimum_test_corpus": [
                "math-deso-11-tb",
                "in/_Toan_2026_Big.docx",
                "in/_Ly_2026_Big.docx",
            ],
            "acceptance_gate": "Only open a production-fix branch after a probe shows a concrete subtype-specific decode rule that materializes SLOT/body records for the dominant family without changing existing renderable FULL->SLOT traces.",
        }
    if label in {"DEGENERATE_OR_CORRUPT_PAYLOAD", "INVESTIGATE_MTEF_STRUCTURAL_DECODING"}:
        return {
            "open_upstream_investigation_branch": False,
            "open_upstream_production_fix_branch": False,
            "ready_for_upstream_fix_hypothesis": False,
            "target_stage": "NONE",
            "reason": "The current evidence does not support a focused upstream fix target yet.",
            "fix_hypothesis": "NONE",
            "risk": "unknown",
            "minimum_test_corpus": [],
            "acceptance_gate": "Gather more corpus evidence first.",
        }
    return {
        "open_upstream_investigation_branch": False,
        "open_upstream_production_fix_branch": False,
        "ready_for_upstream_fix_hypothesis": False,
        "target_stage": "NONE",
        "reason": "Keep gathering corpus evidence before opening a fix branch.",
        "fix_hypothesis": "NONE",
        "risk": "unknown",
        "minimum_test_corpus": [],
        "acceptance_gate": "Gather more corpus evidence first.",
    }


def emit_text(payload: dict) -> None:
    selection = payload["selection"]
    family = payload["family_report"]
    print("DSMT4 FULL_END_ONLY family report:")
    print(
        f"- selection: registry_sources_total={selection['registry_sources_total']} "
        f"external_sources_total={selection['external_sources_total']} "
        f"external_docx_sources_total={selection['external_docx_sources_total']}"
    )
    print(
        f"- family: payload_class_count={family['payload_class_count']} occurrence_count={family['occurrence_count']} "
        f"source_family_count={family['source_family_count']} exact_variant_count={family['exact_variant_count']}"
    )
    print(f"- evidence_label={family['evidence_label']} confidence={family['evidence_confidence']}")
    print(f"- evidence_reason={family['evidence_reason']}")
    print(f"- primary_label={family['primary_label']}")
    print(f"- final_label={family['final_label']}")
    print(
        f"- stage_label={family['stage_assessment']['label']} "
        f"split_point={family['stage_assessment']['first_structural_split_point']}"
    )
    print(f"- stage_reason={family['stage_assessment']['reason']}")
    print(f"- byte_split_visible={family['stage_assessment'].get('byte_split_visible')}")
    print(
        f"- after_full_marker_summary: all_after_full_marker_types_are_end={family['after_full_summary']['all_after_full_marker_types_are_end']} "
        f"raw_byte_probe_fully_verified={family['after_full_summary']['raw_byte_probe_fully_verified']} "
        f"signal={family['after_full_summary']['early_termination_signal']}"
    )
    print(f"- after_full_reason={family['after_full_summary']['early_termination_reason']}")
    print(f"- code_path_decision_point={family['code_path_probe']['decision_point']}")
    print(f"- code_path_implication={family['code_path_probe']['implication']}")
    fingerprint = family["fingerprint_report"]
    print(
        f"- fingerprint_label={fingerprint['final_label']} "
        f"candidate_count={fingerprint['candidate_count']}"
    )
    if fingerprint.get("best_candidate"):
        best = fingerprint["best_candidate"]
        print(
            f"- best_fingerprint={best['key']} type={best['candidate_type']} "
            f"coverage={best['coverage']}/{best['family_total']} "
            f"false_positive_controls={best['false_positive_controls']}/{best['control_total']} "
            f"pre_dispatch={best['pre_dispatch']} brittle={best['brittle']}"
        )
    print(f"- fingerprint_reason={fingerprint['reason']}")
    subtype_poc = family.get("subtype_poc_report")
    if subtype_poc is not None:
        print(
            f"- subtype_poc_label={subtype_poc['final_label']} "
            f"matched_family={subtype_poc['matched_family_count']}/{subtype_poc['family_total']} "
            f"matched_controls={subtype_poc['matched_control_count']}/{subtype_poc['control_total']}"
        )
        print(
            f"- subtype_poc_reason={subtype_poc['reason']} "
            f"controls_trace_preserved={subtype_poc['controls_trace_preserved']} "
            f"additional_parser_stage_evidence_count={subtype_poc['additional_parser_stage_evidence_count']}"
        )
        print(
            f"- subtype_poc_interpretive_pivot: new_interpretive_pivot_detected="
            f"{subtype_poc['interpretive_pivot_summary']['new_interpretive_pivot_detected']} "
            f"family_pivot_labels={subtype_poc['interpretive_pivot_summary']['dominant_family_pivot_labels']} "
            f"control_pivot_labels={subtype_poc['interpretive_pivot_summary']['control_pivot_labels']}"
        )
        print(f"- subtype_poc_hypothesis={subtype_poc['new_interpretation_hypothesis']}")
    recommendation = family["recommendation"]
    print(
        f"- recommendation: open_upstream_investigation_branch={recommendation['open_upstream_investigation_branch']} "
        f"open_upstream_production_fix_branch={recommendation['open_upstream_production_fix_branch']} "
        f"target_stage={recommendation['target_stage']}"
    )
    print(f"- recommendation_reason={recommendation['reason']}")
    print(f"- fix_hypothesis={recommendation['fix_hypothesis']}")
    if family["source_families"]:
        print(f"- source_families={','.join(family['source_families'])}")
    if family["source_names"]:
        print(f"- source_names={','.join(family['source_names'])}")
    if family["structural_subtaxa"]:
        print("Structural subtaxonomy:")
        for group in family["structural_subtaxa"]:
            print(
                f"- {group['subtaxonomy']}: payload_classes={group['payload_class_count']} "
                f"occurrences={group['occurrence_count']} source_families={group['source_family_count']}"
            )
            print(f"  signature={group['signature']}")
    if family["exact_variants"]:
        print("Exact variants:")
        for group in family["exact_variants"]:
            print(
                f"- {group['subtaxonomy']}: payload_classes={group['payload_class_count']} "
                f"occurrences={group['occurrence_count']} source_families={group['source_family_count']} "
                f"checksums={group['checksum_pair'][0]}/{group['checksum_pair'][1]}"
            )
            print(f"  equation_bytes_pair={group['equation_bytes_pair'][0]}/{group['equation_bytes_pair'][1]}")
            print(f"  class_keys={','.join(group['class_keys'])}")
    if family["neighbor_comparisons"]:
        print("Renderable neighbor comparisons:")
        for comparison in family["neighbor_comparisons"]:
            eqn_successor_pair = comparison["signature_diff"]["eqn_prefs_successor_pair"]
            full_successor_pair = comparison["signature_diff"]["full_successor_pair"]
            print(
                f"- family={comparison['family_class_key']} neighbor={comparison['neighbor_class_key']} "
                f"neighbor_pattern={comparison['neighbor_pattern_class']}"
            )
            print(f"  eqn_prefs_successor={eqn_successor_pair[0]}/{eqn_successor_pair[1]}")
            print(f"  full_successor={full_successor_pair[0]}/{full_successor_pair[1]}")
            print(
                f"  record_split={comparison['signature_diff']['record_diff']['left_next']}/"
                f"{comparison['signature_diff']['record_diff']['right_next']} "
                f"shared_prefix={comparison['signature_diff']['record_diff']['shared_prefix_length']}"
            )
            print(
                f"  dispatch_after_full={comparison['dispatch_diff']['after_full_branch_pair'][0]}/"
                f"{comparison['dispatch_diff']['after_full_branch_pair'][1]} "
                f"dispatch_class={comparison['dispatch_diff']['after_full_dispatch_class_pair'][0]}/"
                f"{comparison['dispatch_diff']['after_full_dispatch_class_pair'][1]} "
                f"termination={comparison['dispatch_diff']['termination_pair'][0]}/"
                f"{comparison['dispatch_diff']['termination_pair'][1]}"
            )
            print(
                f"  after_full_offsets={comparison['dispatch_diff']['after_full_offset_pair'][0]}/"
                f"{comparison['dispatch_diff']['after_full_offset_pair'][1]} "
                f"after_full_equation_offsets={comparison['dispatch_diff']['after_full_equation_offset_pair'][0]}/"
                f"{comparison['dispatch_diff']['after_full_equation_offset_pair'][1]} "
                f"after_full_bytes={comparison['dispatch_diff']['after_full_byte_pair'][0]}/"
                f"{comparison['dispatch_diff']['after_full_byte_pair'][1]}"
            )
            print(
                f"  bin_byte_diff=offset:{comparison['bin_byte_diff']['first_diff_offset']} "
                f"left:{comparison['bin_byte_diff']['left_window_hex']} "
                f"right:{comparison['bin_byte_diff']['right_window_hex']}"
            )
            print(
                f"  preview_byte_diff=offset:{comparison['preview_byte_diff']['first_diff_offset']} "
                f"left:{comparison['preview_byte_diff']['left_window_hex']} "
                f"right:{comparison['preview_byte_diff']['right_window_hex']}"
            )
            print(
                f"  family_eqn_prefs={comparison.get('family_eqn_prefs_counts')} "
                f"neighbor_eqn_prefs={comparison.get('neighbor_eqn_prefs_counts')}"
            )
            print(
                f"  family_suffix16={comparison.get('family_effective_suffix_16')} "
                f"neighbor_suffix16={comparison.get('neighbor_effective_suffix_16')}"
            )
    if fingerprint["candidates"]:
        print("Fingerprint candidates:")
        for candidate in fingerprint["candidates"]:
            print(
                f"- {candidate['key']}: strength={candidate['strength']} "
                f"coverage={candidate['coverage']}/{candidate['family_total']} "
                f"false_positive_controls={candidate['false_positive_controls']}/{candidate['control_total']} "
                f"pre_dispatch={candidate['pre_dispatch']} brittle={candidate['brittle']}"
            )
            print(f"  description={candidate['description']}")
            print(f"  dominant_value={candidate['dominant_value']}")
    if subtype_poc is not None:
        print("Subtype-specific POC:")
        print(f"- trigger_name={subtype_poc['trigger_name']}")
        print(f"  trigger_definition={subtype_poc['trigger_definition']}")
        print(f"- interpretive_pivot_summary={subtype_poc['interpretive_pivot_summary']}")
        print(f"- new_interpretation_hypothesis={subtype_poc['new_interpretation_hypothesis']}")
        for entry in subtype_poc["family_entries"]:
            print(
                f"- family={entry['class_key']} trigger_match={entry['trigger']['matches']} "
                f"after_full={entry['bin_after_full_branch']}/{entry['preview_after_full_branch']} "
                f"additional_evidence={entry['additional_parser_stage_evidence']}"
            )
            print(f"  interpretive_pivot={entry['interpretive_pivot']}")
        for entry in subtype_poc["control_entries"]:
            print(
                f"- control={entry['class_key']} trigger_match={entry['trigger']['matches']} "
                f"after_full={entry['bin_after_full_branch']}/{entry['preview_after_full_branch']} "
                f"additional_evidence={entry['additional_parser_stage_evidence']}"
            )
            print(f"  interpretive_pivot={entry['interpretive_pivot']}")


def emit_frozen_baseline_text(payload: dict) -> None:
    dominant = payload["current_dominant_family_baseline"]
    findings = payload["confirmed_findings"]
    trigger = payload["current_strongest_trigger"]
    recommendation = payload["current_action_recommendation"]
    acceptance_gate = recommendation["acceptance_gate"]
    print("Current DSMT4 investigation baseline:")
    print(
        f"- current_dominant_family_baseline={dominant['dominant_family']} "
        f"payload_classes={dominant['payload_class_count']} occurrences={dominant['occurrence_count']} "
        f"source_families={dominant['source_family_count']}"
    )
    print(
        f"- confirmed_findings: evidence_label={findings['evidence_label']} "
        f"action_label={findings['action_label']} "
        f"fingerprint_label={findings['fingerprint_label']} "
        f"poc_label={findings['poc_label']}"
    )
    print(
        f"- decision_point={dominant['decision_point']} "
        f"decision_point_human={dominant['decision_point_human']} "
        f"dispatch_site={dominant['top_level_dispatch_site_human']}"
    )
    print(
        f"- dominant_family_path={dominant['dominant_path']} "
        f"renderable_controls_path={dominant['renderable_controls_path']}"
    )
    print(
        f"- current_strongest_trigger={trigger['trigger_name']} "
        f"coverage={trigger['coverage']} "
        f"false_positive_controls={trigger['false_positive_controls']}"
    )
    print(f"- composite_pre_dispatch={trigger['canonical_signature']}")
    print(
        f"- current_action_recommendation={recommendation['action_label']} "
        f"follow_up_branch_suggestion={recommendation['follow_up_branch_suggestion']}"
    )
    print(f"- recommendation_reason={recommendation['recommendation']}")
    print(
        f"- acceptance_gate: dominant_family_still_matches={acceptance_gate['dominant_family_still_matches']} "
        f"false_positive_controls_stay={acceptance_gate['false_positive_controls_stay']} "
        f"controls_preserve_renderable_path={acceptance_gate['controls_preserve_renderable_path']} "
        f"only_accept_if_new_parser_stage_body_evidence_appears={acceptance_gate['only_accept_if_new_parser_stage_body_evidence_appears']}"
    )
    print("Current non-goals:")
    for item in payload["current_non_goals"]:
        print(f"- {item}")
    print("Handoff answers:")
    for key, value in payload["handoff_answers"].items():
        print(f"- {key}={value}")


if __name__ == "__main__":
    raise SystemExit(main())
