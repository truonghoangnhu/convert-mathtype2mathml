#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_HELPER_PATH = Path(__file__).with_name("audit_dsmt4_corpus.py")

TARGET_PATTERN_CLASS = "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY"
NON_RENDERABLE_COMMENT_TAGS = {"mt_comment", "comment_length", "comment_type", "comment_data"}
NON_RENDERABLE_COMMENT_RECORDS = {"mt_comment"}
RENDERABLE_RECORD_NAMES = {
    "line",
    "char",
    "tmpl",
    "pile",
    "matrix",
    "embell",
    "ruler",
    "sub",
    "sub2",
    "sym",
    "fence",
    "root",
    "fraction",
    "script",
    "slot",
}


def load_audit_helper():
    spec = importlib.util.spec_from_file_location("audit_dsmt4_corpus", AUDIT_HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


AUDIT = load_audit_helper()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Explain EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY cases without changing product behavior."
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
    target_classes = [entry for entry in payload_classes if entry.get("pattern_class") == TARGET_PATTERN_CLASS]
    return summarize_target_family(target_classes)


def renderable_body_tag_counts(summary: dict) -> dict[str, int]:
    tag_counts = dict(summary.get("body_tag_counts") or {})
    return {
        tag: count
        for tag, count in sorted(tag_counts.items())
        if tag not in NON_RENDERABLE_COMMENT_TAGS
    }


def renderable_record_names(parser: dict) -> list[str]:
    names = []
    for record in parser.get("top_level_records") or []:
        name = record.get("name")
        if name in RENDERABLE_RECORD_NAMES and name not in NON_RENDERABLE_COMMENT_RECORDS:
            names.append(str(name))
    return names


def classify_stage_level_root_cause(entry: dict) -> dict:
    deep = entry.get("deep_audit") or {}
    bin_summary = deep.get("bin_mtef_summary") or {}
    preview_summary = deep.get("preview_mtef_summary") or {}
    bin_parser = deep.get("bin_parser") or {}
    preview_parser = deep.get("preview_parser") or {}
    renderable_tags = {
        "bin": renderable_body_tag_counts(bin_summary),
        "preview": renderable_body_tag_counts(preview_summary),
    }
    renderable_records = {
        "bin": renderable_record_names(bin_parser),
        "preview": renderable_record_names(preview_parser),
    }
    any_renderable_before_mathml = bool(renderable_tags["bin"] or renderable_tags["preview"] or renderable_records["bin"] or renderable_records["preview"])
    comment_prefix_present = (
        (bin_parser.get("top_level_records") or [{}])[0].get("name") == "mt_comment"
        or (preview_parser.get("top_level_records") or [{}])[0].get("name") == "mt_comment"
    )
    if any_renderable_before_mathml:
        diagnosis = "CONVERTER_STAGE_CANDIDATE"
        reason = (
            "Renderable math body records/tags are visible before MathML filtering, so loss in the MTEF->MathML or converter stage is the strongest current explanation."
        )
    elif comment_prefix_present:
        diagnosis = "CLASSIFICATION_BOUNDARY_AROUND_MT_COMMENT"
        reason = (
            "The family is classified as body-present because mt_comment/comment tags survive into MTEF XML, but no renderable math body records are visible before MathML generation."
        )
    else:
        diagnosis = "PARSER_STAGE_NO_RENDERABLE_BODY"
        reason = (
            "No renderable body records are visible before MathML generation, so the current issue does not look like a usable-sidecar classification bug."
        )
    return {
        "diagnosis": diagnosis,
        "reason": reason,
        "renderable_body_evidence_before_mathml": any_renderable_before_mathml,
        "renderable_body_tag_counts": renderable_tags,
        "renderable_record_names": renderable_records,
        "mt_comment_prefix_present": comment_prefix_present,
    }


def summarize_target_family(target_classes: list[dict]) -> dict:
    entries = []
    stage_counter = Counter()
    diagnosis_counter = Counter()
    source_files = set()
    parser_pairs = set()
    equation_bytes_pairs = set()
    decision_labels = set()
    for entry in target_classes:
        deep = entry.get("deep_audit") or {}
        signature = entry.get("pattern_signature") or {}
        assessment = entry.get("assessment") or {}
        diagnosis = classify_stage_level_root_cause(entry)
        source_files.update(entry.get("source_names", []))
        parser_pairs.add(tuple([signature.get("bin_parser_class"), signature.get("preview_parser_class")]))
        equation_bytes_pairs.add(tuple([signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")]))
        stage_counter[entry.get("pattern_stage") or "UNKNOWN"] += 1
        diagnosis_counter[diagnosis["diagnosis"]] += 1
        decision_labels.add(assessment.get("decision"))
        entries.append(
            {
                "source_names": entry.get("source_names", []),
                "source_families": entry.get("source_families", []),
                "occurrence_count": entry.get("occurrence_count", 0),
                "class_key": entry.get("class_key"),
                "parser_pair": [signature.get("bin_parser_class"), signature.get("preview_parser_class")],
                "equation_bytes_pair": [signature.get("bin_equation_bytes"), signature.get("preview_equation_bytes")],
                "signature": {
                    "record_sequence": signature.get("bin_top_level_record_sequence"),
                    "tail_after_eqn_prefs": signature.get("bin_tail_after_eqn_prefs"),
                    "bin_sidecar_status": signature.get("bin_sidecar_status"),
                    "preview_sidecar_status": signature.get("preview_sidecar_status"),
                    "same_effective_payload": signature.get("same_effective_payload"),
                },
                "stage_level_diagnosis": diagnosis,
                "decision_label": assessment.get("decision"),
                "decision_reason": assessment.get("reason"),
            }
        )

    total_occurrences = sum(entry["occurrence_count"] for entry in entries)
    parser_pair_values = sorted({tuple(item["parser_pair"]) for item in entries if item["parser_pair"]})
    equation_bytes_values = sorted({tuple(item["equation_bytes_pair"]) for item in entries if item["equation_bytes_pair"]})
    if not entries:
        final_label = "NO_MATCHING_FAMILY_FOUND"
        recommended_next_step = "No matching EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY entry was found in the selected sources."
        open_production_fix_branch = False
        target_stage = "NONE"
    else:
        predominant_diagnosis = diagnosis_counter.most_common(1)[0][0]
        if predominant_diagnosis == "CONVERTER_STAGE_CANDIDATE":
            final_label = "INVESTIGATE_TRANSPECT_CONVERTER"
            recommended_next_step = "Inspect the MTEF->MathML / converter path for this narrow family before considering any default behavior change."
            open_production_fix_branch = False
            target_stage = "CONVERTER_INVESTIGATION"
        elif predominant_diagnosis == "CLASSIFICATION_BOUNDARY_AROUND_MT_COMMENT":
            final_label = "INVESTIGATE_TRANSPECT_CONVERTER"
            recommended_next_step = "Keep this diagnostics-only and verify whether mt_comment/comment tags are being over-read as renderable-body evidence before any converter fix branch."
            open_production_fix_branch = False
            target_stage = "CONVERTER_CLASSIFICATION_BOUNDARY"
        else:
            final_label = "INVESTIGATE_TRANSPECT_CONVERTER"
            recommended_next_step = "Keep this in diagnostics until a later probe finds real renderable math body evidence before MathML generation."
            open_production_fix_branch = False
            target_stage = "NONE"

    return {
        "family": TARGET_PATTERN_CLASS,
        "source_file_count": len(source_files),
        "source_files": sorted(source_files),
        "occurrences": total_occurrences,
        "payload_classes": len(entries),
        "source_families": sorted({family for entry in entries for family in entry["source_families"]}),
        "parser_pairs": [list(value) for value in parser_pair_values],
        "equation_bytes_pairs": [list(value) for value in equation_bytes_values],
        "stage_counts": dict(sorted(stage_counter.items())),
        "stage_level_diagnosis_counts": dict(sorted(diagnosis_counter.items())),
        "entries": entries,
        "final_label": final_label,
        "decision_labels": sorted(label for label in decision_labels if label),
        "recommended_next_step": recommended_next_step,
        "open_production_fix_branch": open_production_fix_branch,
        "target_stage_if_reopened": target_stage,
        "production_fix_gate": (
            "Do not open a production-fix branch unless a later investigation finds stable renderable math body evidence before MathML generation."
        ),
    }


def emit_text(payload: dict) -> None:
    print("EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY report:")
    print(f"- source_files={','.join(payload['source_files']) if payload['source_files'] else 'none'}")
    print(f"- occurrences={payload['occurrences']} payload_classes={payload['payload_classes']}")
    print(f"- source_families={','.join(payload['source_families']) if payload['source_families'] else 'none'}")
    print(f"- parser_pairs={payload['parser_pairs']}")
    print(f"- equation_bytes_pairs={payload['equation_bytes_pairs']}")
    print(f"- stage_counts={payload['stage_counts']}")
    print(f"- stage_level_diagnosis_counts={payload['stage_level_diagnosis_counts']}")
    print(f"- final_label={payload['final_label']}")
    print(f"- decision_labels={payload['decision_labels']}")
    print(f"- recommended_next_step={payload['recommended_next_step']}")
    print(f"- open_production_fix_branch={payload['open_production_fix_branch']} target_stage_if_reopened={payload['target_stage_if_reopened']}")
    print(f"- production_fix_gate={payload['production_fix_gate']}")
    for entry in payload["entries"]:
        print(
            f"- entry class_key={entry['class_key']} occurrences={entry['occurrence_count']} "
            f"parser_pair={entry['parser_pair']} equation_bytes_pair={entry['equation_bytes_pair']}"
        )
        print(f"  signature={entry['signature']}")
        print(f"  stage_level_diagnosis={entry['stage_level_diagnosis']}")
        print(f"  decision_label={entry['decision_label']}")
        print(f"  decision_reason={entry['decision_reason']}")


if __name__ == "__main__":
    raise SystemExit(main())
