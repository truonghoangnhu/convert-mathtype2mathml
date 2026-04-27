#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_HELPER_PATH = Path(__file__).with_name("audit_dsmt4_corpus.py")
TARGET_PATTERN_CLASS = "METADATA_ONLY_NO_RENDERABLE_BODY_OTHER"
FULL_END_ONLY_PATTERN_CLASS = "METADATA_ONLY_FULL_END_ONLY"


def load_audit_helper():
    spec = importlib.util.spec_from_file_location("audit_dsmt4_corpus", AUDIT_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_helper()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deep-audit METADATA_ONLY_NO_RENDERABLE_BODY_OTHER without changing product behavior."
    )
    parser.add_argument("--preset", action="append", default=[], help="Preset name from the smoke preset registry.")
    parser.add_argument("--all-presets", action="store_true", help="Inspect every preset from the smoke preset registry.")
    parser.add_argument("--subject", action="append", default=[], help="Optional subject filter.")
    parser.add_argument("--preset-config", default=str(AUDIT.PRESET_CONFIG), help="Preset registry JSON.")
    parser.add_argument("--extra-workdir", action="append", default=[], help="Additional converted workdir to audit.")
    parser.add_argument("--scan-path", action="append", default=[], help="Scan a directory recursively for extra workdirs containing tmp/state.json.")
    parser.add_argument("--external-docx", action="append", default=[], help="Audit one external DOCX directly by generating/reusing a sidecar workdir.")
    parser.add_argument("--external-dir", action="append", default=[], help="Scan a directory recursively for external .docx files to audit.")
    parser.add_argument("--prefer-underscore-first", action="store_true", help="When scanning external dirs, process underscore-prefixed files first.")
    parser.add_argument("--external-work-root", default=str(AUDIT.DEFAULT_EXTERNAL_AUDIT_ROOT), help="Root directory used to stage generated sidecars.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    args = parser.parse_args()

    try:
        payload = build_payload(args)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        emit_text(payload)
    return 0


def build_payload(args: argparse.Namespace) -> dict:
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
    runtime = AUDIT.EMPTY.discover_runtime() if AUDIT.needs_deep_audit(reports) else None
    payload_classes = AUDIT.classify_payload_classes(reports, runtime)
    family_entries = [entry for entry in payload_classes if entry.get("pattern_class") == TARGET_PATTERN_CLASS]
    full_end_only_entries = [entry for entry in payload_classes if entry.get("pattern_class") == FULL_END_ONLY_PATTERN_CLASS]
    return summarize_target_family(family_entries, full_end_only_entries)


def build_structural_signature(entry: dict) -> dict:
    signature = entry.get("pattern_signature") or {}
    return {
        "stage": signature.get("stage"),
        "assessment_result": signature.get("assessment_result"),
        "assessment_decision": signature.get("assessment_decision"),
        "parser_pair": [signature.get("bin_parser_class"), signature.get("preview_parser_class")],
        "same_effective_payload": signature.get("same_effective_payload"),
        "record_sequence": signature.get("bin_top_level_record_sequence"),
        "tail_after_eqn_prefs": signature.get("bin_tail_after_eqn_prefs"),
        "bin_sidecar_status": signature.get("bin_sidecar_status"),
        "preview_sidecar_status": signature.get("preview_sidecar_status"),
    }


def build_exact_signature(entry: dict) -> dict:
    signature = entry.get("pattern_signature") or {}
    return {
        "bytes_pair": [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")],
        "checksums": [signature.get("bin_checksum"), signature.get("preview_checksum")],
        "record_sequence": signature.get("bin_top_level_record_sequence"),
    }


def relation_to_full_end_only(entry: dict, full_end_only_entries: list[dict]) -> str:
    source_names = set(entry.get("source_names", []))
    signature = entry.get("pattern_signature") or {}
    family_sequence = signature.get("bin_top_level_record_sequence")
    family_tail = signature.get("bin_tail_after_eqn_prefs")
    family_bytes = [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")]
    same_source = [candidate for candidate in full_end_only_entries if source_names & set(candidate.get("source_names", []))]
    exact_shape_match = [
        candidate for candidate in same_source
        if (candidate.get("pattern_signature") or {}).get("bin_top_level_record_sequence") == family_sequence
        and (candidate.get("pattern_signature") or {}).get("bin_tail_after_eqn_prefs") == family_tail
    ]
    if exact_shape_match:
        if any(
            [
                (candidate.get("pattern_signature") or {}).get("bin_equation_bytes"),
                (candidate.get("pattern_signature") or {}).get("preview_equation_bytes"),
            ] == family_bytes
            for candidate in exact_shape_match
        ):
            return "Same-source near-variant of FULL_END_ONLY with matching canonical shape and matching bytes pair."
        return "Same-source near-variant of FULL_END_ONLY with matching canonical shape but different bytes pair."
    if same_source:
        return "Same-source adjacent taxonomy line to FULL_END_ONLY; shared full -> end tail but the local FULL_END_ONLY variant uses a different pre-tail record shape."
    return "No FULL_END_ONLY payload class in the same selected source, but the family still matches the broader canonical full -> end metadata-only shape."


def summarize_target_family(family_entries: list[dict], full_end_only_entries: list[dict]) -> dict:
    if not family_entries:
        return {
            "family": TARGET_PATTERN_CLASS,
            "occurrences": 0,
            "payload_classes": 0,
            "source_files": [],
            "source_families": [],
            "deep_audit_table": [],
            "structural_signature_groups": [],
            "exact_signature_groups": [],
            "canonical_signature": {
                "present": False,
                "reason": "No matching payload class was found in the selected sources.",
            },
            "dominant_signature": None,
            "relation_to_full_end_only": "No matching payload class was found in the selected sources.",
            "decision_label": "NO_MATCHING_FAMILY_FOUND",
            "recommendation": "No action.",
            "open_investigation_branch": False,
            "target_stage_if_reopened": "NONE",
            "rerun_gate": "No matching family was found.",
        }

    structural_groups = {}
    exact_groups = {}
    per_source = {}
    total_occurrences = 0
    source_families = set()
    exact_bytes_counter = Counter()

    for entry in family_entries:
        source_name = entry.get("source_names", ["unknown"])[0]
        signature = entry.get("pattern_signature") or {}
        structural = build_structural_signature(entry)
        exact = build_exact_signature(entry)
        structural_key = json.dumps(structural, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        exact_key = json.dumps(exact, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

        structural_group = structural_groups.setdefault(
            structural_key,
            {
                "signature": structural,
                "payload_classes": 0,
                "occurrences": 0,
                "source_families": set(),
                "source_names": set(),
            },
        )
        structural_group["payload_classes"] += 1
        structural_group["occurrences"] += entry.get("occurrence_count", 0)
        structural_group["source_families"].update(entry.get("source_families", []))
        structural_group["source_names"].update(entry.get("source_names", []))

        exact_group = exact_groups.setdefault(
            exact_key,
            {
                "signature": exact,
                "payload_classes": 0,
                "occurrences": 0,
                "source_families": set(),
                "source_names": set(),
            },
        )
        exact_group["payload_classes"] += 1
        exact_group["occurrences"] += entry.get("occurrence_count", 0)
        exact_group["source_families"].update(entry.get("source_families", []))
        exact_group["source_names"].update(entry.get("source_names", []))

        bytes_pair = tuple(exact["bytes_pair"])
        exact_bytes_counter[bytes_pair] += entry.get("occurrence_count", 0)

        total_occurrences += entry.get("occurrence_count", 0)
        source_families.update(entry.get("source_families", []))

        row = per_source.setdefault(
            source_name,
            {
                "source_file": source_name,
                "occurrences": 0,
                "payload_classes": 0,
                "source_families": set(),
                "stages": set(),
                "bytes_pairs": set(),
                "main_signatures": set(),
                "assessment_labels": set(),
                "decision_labels": set(),
                "relations_to_full_end_only": set(),
            },
        )
        row["occurrences"] += entry.get("occurrence_count", 0)
        row["payload_classes"] += 1
        row["source_families"].update(entry.get("source_families", []))
        row["stages"].add(signature.get("stage"))
        row["bytes_pairs"].add(tuple(exact["bytes_pair"]))
        row["main_signatures"].add(",".join(signature.get("bin_top_level_record_sequence") or []))
        assessment = entry.get("assessment") or {}
        row["assessment_labels"].add(f"{assessment.get('result')} / {assessment.get('decision')}")
        row["decision_labels"].add(assessment.get("decision"))
        row["relations_to_full_end_only"].add(relation_to_full_end_only(entry, full_end_only_entries))

    structural_signature_groups = sorted(
        [
            {
                "signature": group["signature"],
                "payload_classes": group["payload_classes"],
                "occurrences": group["occurrences"],
                "source_families": sorted(group["source_families"]),
                "source_files": sorted(group["source_names"]),
            }
            for group in structural_groups.values()
        ],
        key=lambda group: (-group["payload_classes"], -group["occurrences"], json.dumps(group["signature"], sort_keys=True)),
    )
    exact_signature_groups = sorted(
        [
            {
                "signature": group["signature"],
                "payload_classes": group["payload_classes"],
                "occurrences": group["occurrences"],
                "source_families": sorted(group["source_families"]),
                "source_files": sorted(group["source_names"]),
            }
            for group in exact_groups.values()
        ],
        key=lambda group: (-group["payload_classes"], -group["occurrences"], json.dumps(group["signature"], sort_keys=True)),
    )

    deep_audit_table = sorted(
        [
            {
                "source_file": row["source_file"],
                "occurrences": row["occurrences"],
                "payload_classes": row["payload_classes"],
                "source_families": sorted(row["source_families"]),
                "stage": sorted(stage for stage in row["stages"] if stage),
                "bytes_pairs": [list(value) for value in sorted(row["bytes_pairs"])],
                "main_signature_pattern": sorted(row["main_signatures"]),
                "assessment_decision_label": sorted(label for label in row["assessment_labels"] if label),
                "relation_to_metadata_only_full_end_only": sorted(row["relations_to_full_end_only"]),
                "recommendation": "Keep taxonomy-only; treat as a near-FULL_END_ONLY metadata-only variant unless a later audit finds a stable new split point.",
            }
            for row in per_source.values()
        ],
        key=lambda row: (-row["occurrences"], -row["payload_classes"], row["source_file"]),
    )

    dominant_structural = structural_signature_groups[0]
    dominant_exact = exact_signature_groups[0]
    canonical_signature_present = len(structural_signature_groups) == 1
    dominant_bytes_pair = list(max(exact_bytes_counter.items(), key=lambda item: (item[1], item[0]))[0])

    exact_shape_overlap_with_full_end_only = [
        entry for entry in full_end_only_entries
        if (entry.get("pattern_signature") or {}).get("bin_top_level_record_sequence") == dominant_structural["signature"]["record_sequence"]
        and (entry.get("pattern_signature") or {}).get("bin_tail_after_eqn_prefs") == dominant_structural["signature"]["tail_after_eqn_prefs"]
    ]
    if exact_shape_overlap_with_full_end_only:
        relation_summary = (
            "This family is best treated as a near-FULL_END_ONLY classification variant: it shares the canonical metadata-only full -> end shape, "
            "but lands at PARSER_STAGE / METADATA_ONLY_MTEF_XML instead of PARSER_INPUT_PAYLOAD / TOP_LEVEL_FULL_END_ONLY."
        )
    else:
        relation_summary = (
            "This family stays very close to FULL_END_ONLY by tail shape and metadata-only evidence, but the current selected set does not prove an exact canonical-shape overlap."
        )

    decision_label = "KEEP_TAXONOMY_ONLY_NEAR_FULL_END_ONLY"
    recommendation = (
        "Do not open a production fix or a broader investigation branch yet. Keep this as a focused taxonomy/deep-audit line until a later probe finds a stable split point beyond the current FULL_END_ONLY-near metadata-only shape."
    )

    return {
        "family": TARGET_PATTERN_CLASS,
        "occurrences": total_occurrences,
        "payload_classes": len(family_entries),
        "source_files": sorted(per_source),
        "source_families": sorted(source_families),
        "deep_audit_table": deep_audit_table,
        "structural_signature_groups": structural_signature_groups,
        "exact_signature_groups": exact_signature_groups,
        "canonical_signature": {
            "present": canonical_signature_present,
            "dominant_structural_signature": dominant_structural["signature"],
            "reason": (
                "All selected payload classes collapse to one structural signature."
                if canonical_signature_present
                else "Multiple structural signatures are still present."
            ),
        },
        "dominant_signature": {
            "structural_signature": dominant_structural["signature"],
            "exact_signature": dominant_exact["signature"],
            "dominant_bytes_pair": dominant_bytes_pair,
            "payload_classes": dominant_exact["payload_classes"],
            "occurrences": dominant_exact["occurrences"],
        },
        "relation_to_full_end_only": relation_summary,
        "is_separate_line_vs_variant": (
            "Near-FULL_END_ONLY classification variant"
            if exact_shape_overlap_with_full_end_only
            else "Taxonomy-adjacent metadata-only line"
        ),
        "investigation_candidate_now": False,
        "decision_label": decision_label,
        "recommendation": recommendation,
        "open_investigation_branch": False,
        "target_stage_if_reopened": "PARSER_STAGE_VS_PARSER_INPUT_BOUNDARY",
        "rerun_gate": (
            "Only reopen as a broader investigation candidate if a later audit finds a stable structural split from FULL_END_ONLY or exposes new parser-stage/body evidence."
        ),
    }


def emit_text(payload: dict) -> None:
    print("METADATA_ONLY_NO_RENDERABLE_BODY_OTHER deep-audit:")
    print(f"- source_files={','.join(payload['source_files']) if payload['source_files'] else 'none'}")
    print(f"- occurrences={payload['occurrences']} payload_classes={payload['payload_classes']}")
    print(f"- source_families={','.join(payload['source_families']) if payload['source_families'] else 'none'}")
    print(f"- decision_label={payload['decision_label']}")
    print(f"- investigation_candidate_now={payload['investigation_candidate_now']}")
    print(f"- target_stage_if_reopened={payload['target_stage_if_reopened']}")
    print(f"- relation_to_full_end_only={payload['relation_to_full_end_only']}")
    print(f"- recommendation={payload['recommendation']}")
    print(f"- rerun_gate={payload['rerun_gate']}")
    print(f"- canonical_signature={payload['canonical_signature']}")
    print(f"- dominant_signature={payload['dominant_signature']}")
    print("Deep-audit table:")
    for row in payload["deep_audit_table"]:
        print(
            f"- source_file={row['source_file']} occurrences={row['occurrences']} payload_classes={row['payload_classes']} "
            f"source_families={row['source_families']} stage={row['stage']} bytes_pairs={row['bytes_pairs']}"
        )
        print(f"  main_signature_pattern={row['main_signature_pattern']}")
        print(f"  assessment_decision_label={row['assessment_decision_label']}")
        print(f"  relation_to_metadata_only_full_end_only={row['relation_to_metadata_only_full_end_only']}")
        print(f"  recommendation={row['recommendation']}")
    print("Structural signature groups:")
    for group in payload["structural_signature_groups"]:
        print(
            f"- payload_classes={group['payload_classes']} occurrences={group['occurrences']} "
            f"source_families={group['source_families']} source_files={group['source_files']}"
        )
        print(f"  signature={group['signature']}")
    print("Exact signature groups:")
    for group in payload["exact_signature_groups"]:
        print(
            f"- payload_classes={group['payload_classes']} occurrences={group['occurrences']} "
            f"source_families={group['source_families']} source_files={group['source_files']}"
        )
        print(f"  signature={group['signature']}")


if __name__ == "__main__":
    raise SystemExit(main())
