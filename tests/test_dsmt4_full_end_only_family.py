from __future__ import annotations

import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "explain_dsmt4_full_end_only_family.py"
SPEC = importlib.util.spec_from_file_location("explain_dsmt4_full_end_only_family", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def canonical_signature(*, bin_checksum: str, preview_checksum: str) -> dict:
    return {
        "stage": "PARSER_INPUT_PAYLOAD",
        "same_effective_payload": True,
        "bin_parser_class": "Mathtype::OleFileParser",
        "preview_parser_class": "Mathtype::WmfFileParser",
        "bin_equation_bytes": 193,
        "preview_equation_bytes": 194,
        "bin_checksum": bin_checksum,
        "preview_checksum": preview_checksum,
        "bin_top_level_record_sequence": list(MODULE.CANONICAL_RECORD_SEQUENCE),
        "preview_top_level_record_sequence": list(MODULE.CANONICAL_RECORD_SEQUENCE),
        "bin_tail_after_eqn_prefs": list(MODULE.CANONICAL_TAIL),
        "preview_tail_after_eqn_prefs": list(MODULE.CANONICAL_TAIL),
        "bin_top_level_mtef_xml_tags": [
            "mtef_version",
            "platform",
            "product",
            "product_version",
            "product_subversion",
            "application_key",
            "equation_options",
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "end",
        ],
        "preview_top_level_mtef_xml_tags": [
            "mtef_version",
            "platform",
            "product",
            "product_version",
            "product_subversion",
            "application_key",
            "equation_options",
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "end",
        ],
    }


def renderable_signature() -> dict:
    return {
        **canonical_signature(bin_checksum="9999", preview_checksum="999A"),
        "bin_top_level_record_sequence": [
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "slot",
            "end",
        ],
        "preview_top_level_record_sequence": [
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "slot",
            "end",
        ],
        "bin_tail_after_eqn_prefs": ["full", "slot", "end"],
        "preview_tail_after_eqn_prefs": ["full", "slot", "end"],
        "bin_top_level_mtef_xml_tags": [
            "mtef_version",
            "platform",
            "product",
            "product_version",
            "product_subversion",
            "application_key",
            "equation_options",
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "slot",
            "end",
        ],
        "preview_top_level_mtef_xml_tags": [
            "mtef_version",
            "platform",
            "product",
            "product_version",
            "product_subversion",
            "application_key",
            "equation_options",
            "encoding_def",
            "font_def",
            "font_def",
            "font_def",
            "font_def",
            "eqn_prefs",
            "full",
            "slot",
            "end",
        ],
    }


class Dsmt4FullEndOnlyFamilyTest(unittest.TestCase):
    def test_record_prefix_before_dispatch_stops_at_full(self) -> None:
        prefix = MODULE.record_prefix_before_dispatch(
            ["encoding_def", "font_def", "font_def", "eqn_prefs", "full", "slot", "end"]
        )

        self.assertEqual(prefix, ("encoding_def", "font_def", "font_def", "eqn_prefs", "full"))

    def test_candidate_strength_marks_full_coverage_zero_false_positive_as_strong(self) -> None:
        strength = MODULE.candidate_strength(
            coverage=3,
            total_family=3,
            false_positives=0,
            pre_dispatch=True,
            brittle=False,
        )

        self.assertEqual(strength, "STRONG_PRE_DISPATCH_FINGERPRINT")

    def test_evaluate_composite_pre_dispatch_trigger_requires_all_fields(self) -> None:
        matching = MODULE.evaluate_composite_pre_dispatch_trigger(
            {
                "parser_pair": ("Mathtype::OleFileParser", "Mathtype::WmfFileParser"),
                "same_effective_payload": True,
                "equation_bytes_pair": (193, 194),
                "record_prefix_before_dispatch": (
                    "encoding_def",
                    "font_def",
                    "font_def",
                    "font_def",
                    "font_def",
                    "eqn_prefs",
                    "full",
                ),
                "eqn_prefs_shape": (8, 30, 12),
            }
        )
        non_matching = MODULE.evaluate_composite_pre_dispatch_trigger(
            {
                "parser_pair": ("Mathtype::OleFileParser", "Mathtype::WmfFileParser"),
                "same_effective_payload": True,
                "equation_bytes_pair": (193, 194),
                "record_prefix_before_dispatch": (
                    "encoding_def",
                    "font_def",
                    "font_def",
                    "font_def",
                    "eqn_prefs",
                    "full",
                ),
                "eqn_prefs_shape": (8, 30, 12),
            }
        )

        self.assertTrue(matching["matches"])
        self.assertFalse(non_matching["matches"])
        self.assertFalse(non_matching["field_matches"]["record_prefix_before_dispatch"])

    def test_classify_structural_subtaxonomy_marks_canonical_signature(self) -> None:
        taxonomy = MODULE.classify_structural_subtaxonomy(canonical_signature(bin_checksum="35F3", preview_checksum="35FD"))
        self.assertEqual(taxonomy, "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL")

    def test_classify_exact_variant_collapses_checksum_variants_into_same_byte_family(self) -> None:
        taxonomy = MODULE.classify_exact_variant(canonical_signature(bin_checksum="35EF", preview_checksum="35F9"))
        self.assertEqual(taxonomy, "FULL_END_ONLY_CANONICAL_193_194")

    def test_assess_evidence_prefers_unsupported_subtype_for_single_structural_family(self) -> None:
        structural_subtaxa = [
            {
                "subtaxonomy": "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL",
                "payload_class_count": 3,
                "occurrence_count": 5,
                "source_family_count": 3,
            }
        ]
        exact_variants = [
            {"subtaxonomy": "FULL_END_ONLY_CANONICAL_193_194", "payload_class_count": 2},
            {"subtaxonomy": "FULL_END_ONLY_CANONICAL_193_194", "payload_class_count": 1},
        ]

        evidence = MODULE.assess_evidence(3, structural_subtaxa, exact_variants)

        self.assertEqual(evidence["label"], "UNSUPPORTED_SUBTYPE")
        self.assertEqual(evidence["confidence"], "medium")

    def test_assess_stage_boundary_prefers_parser_input_interpretation_when_split_is_after_eqn_prefs(self) -> None:
        family_payload_classes = [
            {
                "pattern_signature": canonical_signature(bin_checksum="35F3", preview_checksum="35FD"),
            }
        ]
        neighbor_comparisons = [
            {
                "signature_diff": {
                    "eqn_prefs_successor_pair": ["full", "full"],
                    "full_successor_pair": ["end", "slot"],
                    "record_diff": {"shared_prefix_length": 7, "left_next": "end", "right_next": "slot"},
                }
            }
        ]

        stage = MODULE.assess_stage_boundary(family_payload_classes, neighbor_comparisons)

        self.assertEqual(stage["label"], "INVESTIGATE_PARSER_INPUT_INTERPRETATION")
        self.assertEqual(stage["first_structural_split_point"], "FIRST_RECORD_AFTER_FULL")
        self.assertFalse(stage["payload_has_body_records_at_parser_input"])

    def test_compare_signatures_marks_first_record_split_after_eqn_prefs(self) -> None:
        diff = MODULE.compare_signatures(canonical_signature(bin_checksum="35F3", preview_checksum="35FD"), renderable_signature())

        self.assertEqual(diff["eqn_prefs_successor_pair"], ["full", "full"])
        self.assertEqual(diff["full_successor_pair"], ["end", "slot"])
        self.assertEqual(diff["record_diff"]["shared_prefix_length"], 7)
        self.assertEqual(diff["record_diff"]["left_next"], "end")
        self.assertEqual(diff["record_diff"]["right_next"], "slot")

    def test_compare_hex_streams_reports_first_diff_window(self) -> None:
        diff = MODULE.compare_hex_streams("0102030a00", "0102030b01")

        self.assertEqual(diff["first_diff_offset"], 3)
        self.assertEqual(diff["shared_prefix_bytes"], 3)
        self.assertTrue(diff["left_window_hex"])
        self.assertTrue(diff["right_window_hex"])

    def test_build_code_path_probe_marks_full_as_zero_payload_marker(self) -> None:
        probe = MODULE.build_code_path_probe()

        self.assertIn("RecordFull is an empty typesize marker", probe["full_record_definition_location"])
        self.assertEqual(probe["record_type_mapping"]["full"], 10)
        self.assertEqual(probe["record_type_mapping"]["slot"], 1)

    def test_choose_final_label_prefers_unsupported_subtype_when_full_has_no_branch_payload(self) -> None:
        label = MODULE.choose_final_label(
            evidence_label="UNSUPPORTED_SUBTYPE",
            stage_label="INVESTIGATE_PARSER_INPUT_INTERPRETATION",
            code_path_probe=MODULE.build_code_path_probe(),
        )

        self.assertEqual(label, "UNSUPPORTED_SUBTYPE")

    def test_build_after_full_dispatch_probe_reports_end_vs_slot_transition(self) -> None:
        family_probe = MODULE.build_after_full_dispatch_probe(
            {
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 18, "name": "eqn_prefs", "record_abs_offset": 0, "record_num_bytes": 4},
                    {"index": 1, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 2, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": None, "payload_num_bytes": None},
                ]
            },
            "000000000000000000000000120304050a00",
        )
        neighbor_probe = MODULE.build_after_full_dispatch_probe(
            {
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 18, "name": "eqn_prefs", "record_abs_offset": 0, "record_num_bytes": 4},
                    {"index": 1, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 2, "record_type": 1, "name": "slot", "record_abs_offset": 5, "record_num_bytes": 3, "payload_class": "Mathtype5::RecordLine", "payload_num_bytes": 2, "child_list_field": "object_list", "child_records": [{"record_type": 0, "name": "end"}]},
                ]
            },
            "000000000000000000000000120304050a010000",
        )

        self.assertEqual(family_probe["next_record"]["name"], "end")
        self.assertEqual(family_probe["next_record_equation_offset"], 17)
        self.assertEqual(family_probe["next_record_type_byte_at_offset"], 0)
        self.assertEqual(family_probe["raw_marker_probe_status"], "verified")
        self.assertEqual(family_probe["termination_condition"], "READ_UNTIL_END_RECORD_TYPE_0")
        self.assertEqual(neighbor_probe["next_record"]["name"], "slot")
        self.assertEqual(neighbor_probe["next_record"]["payload_class"], "Mathtype5::RecordLine")
        self.assertEqual(neighbor_probe["next_record_equation_offset"], 17)
        self.assertEqual(neighbor_probe["next_record_type_byte_at_offset"], 1)
        self.assertEqual(neighbor_probe["raw_marker_probe_status"], "verified")

        dispatch_diff = MODULE.compare_dispatch_probes(family_probe, neighbor_probe)

        self.assertEqual(dispatch_diff["after_full_branch_pair"], ["end", "slot"])
        self.assertEqual(dispatch_diff["after_full_dispatch_class_pair"], [None, "Mathtype5::RecordLine"])
        self.assertEqual(dispatch_diff["after_full_equation_offset_pair"], [17, 17])
        self.assertEqual(
            dispatch_diff["termination_pair"],
            ["READ_UNTIL_END_RECORD_TYPE_0", "CONTINUE_INTO_SLOT"],
        )

    def test_summarize_interpretive_pivot_reports_no_new_pivot_when_triggered_family_still_hits_end(self) -> None:
        trigger = MODULE.evaluate_composite_pre_dispatch_trigger(
            {
                "parser_pair": ("Mathtype::OleFileParser", "Mathtype::WmfFileParser"),
                "same_effective_payload": True,
                "equation_bytes_pair": (193, 194),
                "record_prefix_before_dispatch": (
                    "encoding_def",
                    "font_def",
                    "font_def",
                    "font_def",
                    "font_def",
                    "eqn_prefs",
                    "full",
                ),
                "eqn_prefs_shape": (8, 30, 12),
            }
        )
        family_probe = MODULE.build_after_full_dispatch_probe(
            {
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 18, "name": "eqn_prefs", "record_abs_offset": 0, "record_num_bytes": 4},
                    {"index": 1, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 2, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": None, "payload_num_bytes": None},
                ],
            },
            "000000000000000000000000120304050a00",
        )

        pivot = MODULE.summarize_interpretive_pivot(
            trigger=trigger,
            bin_probe=family_probe,
            preview_probe=family_probe,
        )

        self.assertTrue(pivot["trigger_matched"])
        self.assertEqual(pivot["next_marker_byte_pair"], [0, 0])
        self.assertEqual(pivot["dispatch_choice_pair"], ["end", "end"])
        self.assertFalse(pivot["alternate_branch_visible"])
        self.assertEqual(pivot["pivot_label"], "NO_NEW_PIVOT_BEYOND_FIRST_RECORD_AFTER_FULL")

    def test_summarize_after_full_markers_marks_indirect_only_when_all_bytes_are_zero(self) -> None:
        family_payload_classes = [
            {
                "class_key": "a|b",
                "source_families": ["math-deso-11-tb"],
                "source_names": ["math-deso-11-tb"],
            }
        ]
        deep = {
            "bin_parser": {
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 1, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordEnd", "payload_num_bytes": 0},
                ],
            },
            "preview_parser": {
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 1, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordEnd", "payload_num_bytes": 0},
                ],
            },
            "bin_equation_hex": "000000000000000000000000120304050a00",
            "preview_equation_hex": "000000000000000000000000120304050a00",
        }
        with patch.object(MODULE, "deep_inspect_payload_class", return_value=deep):
            summary = MODULE.summarize_after_full_markers(family_payload_classes, runtime={}, source_input_map={})

        self.assertEqual(summary["entry_count"], 1)
        self.assertTrue(summary["all_after_full_marker_types_are_end"])
        self.assertTrue(summary["raw_byte_probe_fully_verified"])
        self.assertEqual(summary["early_termination_signal"], "INDIRECT_ONLY")

    def test_choose_primary_label_prefers_stage_label_until_fix_branch_is_ready(self) -> None:
        label = MODULE.choose_primary_label(
            {"label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION"},
            {"open_upstream_production_fix_branch": False},
        )

        self.assertEqual(label, "INVESTIGATE_PARSER_INPUT_INTERPRETATION")

    def test_summarize_family_reports_structural_and_exact_variants(self) -> None:
        family_payload_classes = [
            {
                "class_key": "a|p",
                "occurrence_count": 2,
                "source_names": ["math-deso-11-tb"],
                "source_families": ["Toan_deso_11_TB"],
                "pattern_signature": canonical_signature(bin_checksum="35F3", preview_checksum="35FD"),
            },
            {
                "class_key": "b|p",
                "occurrence_count": 2,
                "source_names": ["external-docx:in/_Toan_2026_Big.docx"],
                "source_families": ["_Toan_2026_Big"],
                "pattern_signature": canonical_signature(bin_checksum="35F3", preview_checksum="35FD"),
            },
            {
                "class_key": "c|q",
                "occurrence_count": 1,
                "source_names": ["external-docx:in/_Ly_2026_Big.docx"],
                "source_families": ["_Ly_2026_Big"],
                "pattern_signature": canonical_signature(bin_checksum="35EF", preview_checksum="35F9"),
            },
        ]
        neighbor_comparisons = [
            {
                "family_class_key": "a|p",
                "neighbor_class_key": "r|s",
                "neighbor_pattern_class": "RENDERABLE_BODY_PRESENT",
                "signature_diff": {
                    "eqn_prefs_successor_pair": ["full", "full"],
                    "full_successor_pair": ["end", "slot"],
                    "record_diff": {"shared_prefix_length": 7, "left_next": "end", "right_next": "slot"},
                },
                "dispatch_diff": {
                    "after_full_branch_pair": ["end", "slot"],
                    "after_full_dispatch_class_pair": [None, "Mathtype5::RecordLine"],
                    "after_full_equation_offset_pair": [17, 17],
                    "termination_pair": ["READ_UNTIL_END_RECORD_TYPE_0", "CONTINUE_INTO_SLOT"],
                },
                "bin_byte_diff": {"first_diff_offset": 12, "left_window_hex": "aa", "right_window_hex": "bb"},
                "preview_byte_diff": {"first_diff_offset": 12, "left_window_hex": "aa", "right_window_hex": "bb"},
            }
        ]

        after_full_summary = {
            "entry_count": 3,
            "all_after_full_marker_types_are_end": True,
            "raw_byte_probe_fully_verified": False,
            "early_termination_signal": "INDIRECT_ONLY",
            "early_termination_reason": "indirect",
        }
        fingerprint_report = {
            "final_label": "STRONG_PRE_DISPATCH_FINGERPRINT",
            "reason": "strong",
            "candidate_count": 1,
            "candidates": [],
            "best_candidate": {
                "key": "composite_pre_dispatch",
                "candidate_type": "composite",
                "coverage": 3,
                "family_total": 3,
                "false_positive_controls": 0,
                "control_total": 1,
                "pre_dispatch": True,
                "brittle": False,
            },
        }

        with patch.object(MODULE, "compare_with_renderable_neighbors", return_value=neighbor_comparisons), patch.object(
            MODULE, "summarize_after_full_markers", return_value=after_full_summary
        ), patch.object(MODULE, "summarize_fingerprint_candidates", return_value=fingerprint_report):
            summary = MODULE.summarize_family(
                family_payload_classes,
                renderable_payload_classes=[],
                runtime={},
                source_input_map={},
            )

        self.assertEqual(summary["payload_class_count"], 3)
        self.assertEqual(summary["source_family_count"], 3)
        self.assertEqual(summary["structural_subtaxonomy_count"], 1)
        self.assertEqual(summary["exact_variant_count"], 2)
        self.assertEqual(summary["primary_label"], "INVESTIGATE_PARSER_INPUT_INTERPRETATION")
        self.assertEqual(summary["final_label"], "UNSUPPORTED_SUBTYPE")
        self.assertEqual(summary["evidence_label"], "UNSUPPORTED_SUBTYPE")
        self.assertEqual(summary["stage_assessment"]["label"], "INVESTIGATE_PARSER_INPUT_INTERPRETATION")
        self.assertEqual(summary["after_full_summary"]["early_termination_signal"], "INDIRECT_ONLY")
        self.assertEqual(summary["fingerprint_report"]["final_label"], "STRONG_PRE_DISPATCH_FINGERPRINT")
        self.assertTrue(summary["stage_assessment"]["byte_split_visible"])
        self.assertTrue(summary["recommendation"]["open_upstream_investigation_branch"])
        self.assertFalse(summary["recommendation"]["open_upstream_production_fix_branch"])

    def test_summarize_fingerprint_candidates_prefers_composite_pre_dispatch_signature(self) -> None:
        family_payload_classes = [
            {
                "class_key": "a|p",
                "source_families": ["Toan_deso_11_TB"],
            },
            {
                "class_key": "b|p",
                "source_families": ["_Toan_2026_Big"],
            },
            {
                "class_key": "c|q",
                "source_families": ["_Ly_2026_Big"],
            },
        ]
        canonical = canonical_signature(bin_checksum="35F3", preview_checksum="35FD")
        family_deep = {
            "pattern_signature": canonical,
            "bin_parser": {"eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12}},
            "preview_parser": {"eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12}},
            "bin_equation_hex": "00020001010100030001000400000a00",
            "preview_equation_hex": "00020001010100030001000400000a00",
        }
        neighbor_comparisons = [
            {
                "neighbor_class_key": "n1",
                "neighbor_source_families": ["Toan_deso_11_TB"],
                "neighbor_signature": {
                    "parser_pair": ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"],
                    "same_effective_payload": True,
                    "equation_bytes_pair": [199, 200],
                    "top_level_record_sequence": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                    "top_level_mtef_xml_tags": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                },
                "neighbor_eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "neighbor_effective_suffix_8": "00837a0000000a00",
                "neighbor_effective_suffix_12": "00000a01000200837a000000",
                "neighbor_effective_suffix_16": "01000400000a01000200837a0000000a",
            },
            {
                "neighbor_class_key": "n2",
                "neighbor_source_families": ["_Toan_2026_Big"],
                "neighbor_signature": {
                    "parser_pair": ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"],
                    "same_effective_payload": True,
                    "equation_bytes_pair": [192, 193],
                    "top_level_record_sequence": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                    "top_level_mtef_xml_tags": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                },
                "neighbor_eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "neighbor_effective_suffix_8": "0200883300000000",
                "neighbor_effective_suffix_12": "008834000200883300000000",
                "neighbor_effective_suffix_16": "0a010002008834000200883300000000",
            },
            {
                "neighbor_class_key": "n3",
                "neighbor_source_families": ["_Ly_2026_Big"],
                "neighbor_signature": {
                    "parser_pair": ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"],
                    "same_effective_payload": True,
                    "equation_bytes_pair": [194, 195],
                    "top_level_record_sequence": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                    "top_level_mtef_xml_tags": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                },
                "neighbor_eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "neighbor_effective_suffix_8": "020083470000004e",
                "neighbor_effective_suffix_12": "00834500020083470000004e",
                "neighbor_effective_suffix_16": "0a01000200834500020083470000004e",
            },
        ]

        with patch.object(MODULE, "deep_inspect_payload_class", return_value=family_deep):
            report = MODULE.summarize_fingerprint_candidates(
                family_payload_classes,
                neighbor_comparisons,
                runtime={},
                source_input_map={},
            )

        self.assertEqual(report["final_label"], "STRONG_PRE_DISPATCH_FINGERPRINT")
        self.assertEqual(report["best_candidate"]["key"], "composite_pre_dispatch")
        self.assertEqual(report["best_candidate"]["coverage"], 3)
        self.assertEqual(report["best_candidate"]["false_positive_controls"], 0)
        eqn_prefs_candidate = next(item for item in report["candidates"] if item["key"] == "eqn_prefs_shape")
        self.assertEqual(eqn_prefs_candidate["false_positive_controls"], 3)
        self.assertEqual(eqn_prefs_candidate["strength"], "NO_USEFUL_FINGERPRINT")
        suffix_candidate = next(item for item in report["candidates"] if item["key"] == "effective_suffix_16")
        self.assertEqual(suffix_candidate["false_positive_controls"], 0)
        self.assertEqual(suffix_candidate["strength"], "WEAK_PRE_DISPATCH_FINGERPRINT")

    def test_build_candidate_result_without_controls_downgrades_strength(self) -> None:
        candidate = MODULE.build_candidate_result(
            key="composite",
            candidate_type="composite",
            family_shapes=[
                {
                    "parser_pair": ("Mathtype::OleFileParser", "Mathtype::WmfFileParser"),
                    "same_effective_payload": True,
                    "equation_bytes_pair": (193, 194),
                    "record_prefix_before_dispatch": ("encoding_def", "font_def", "eqn_prefs", "full"),
                    "eqn_prefs_shape": (8, 30, 12),
                }
            ],
            control_shapes=[],
            extractor=lambda shape: (
                shape["parser_pair"],
                shape["same_effective_payload"],
                shape["equation_bytes_pair"],
                shape["record_prefix_before_dispatch"],
                shape["eqn_prefs_shape"],
            ),
            pre_dispatch=True,
            brittle=False,
            description="test",
        )

        self.assertEqual(candidate["strength"], "WEAK_PRE_DISPATCH_FINGERPRINT")

    def test_summarize_subtype_specific_poc_reports_no_additional_evidence_when_controls_do_not_match(self) -> None:
        family_payload_classes = [
            {"class_key": "a|p", "source_families": ["Toan_deso_11_TB"]},
            {"class_key": "b|p", "source_families": ["_Toan_2026_Big"]},
            {"class_key": "c|q", "source_families": ["_Ly_2026_Big"]},
        ]
        family_deep = {
            "pattern_signature": canonical_signature(bin_checksum="35F3", preview_checksum="35FD"),
            "bin_parser": {
                "eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 18, "name": "eqn_prefs", "record_abs_offset": 0, "record_num_bytes": 4},
                    {"index": 1, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 2, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": None, "payload_num_bytes": 0},
                ],
            },
            "preview_parser": {
                "eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "equation_records_start_offset": 12,
                "top_level_records": [
                    {"index": 0, "record_type": 18, "name": "eqn_prefs", "record_abs_offset": 0, "record_num_bytes": 4},
                    {"index": 1, "record_type": 10, "name": "full", "record_abs_offset": 4, "record_num_bytes": 1, "payload_class": "Mathtype5::RecordFull", "payload_num_bytes": 0},
                    {"index": 2, "record_type": 0, "name": "end", "record_abs_offset": 5, "record_num_bytes": 1, "payload_class": None, "payload_num_bytes": 0},
                ],
            },
            "bin_equation_hex": "000000000000000000000000120304050a00",
            "preview_equation_hex": "000000000000000000000000120304050a00",
        }
        neighbor_comparisons = [
            {
                "neighbor_class_key": "n1",
                "neighbor_source_families": ["Toan_deso_11_TB"],
                "neighbor_signature": {
                    "parser_pair": ["Mathtype::OleFileParser", "Mathtype::WmfFileParser"],
                    "same_effective_payload": True,
                    "equation_bytes_pair": [199, 200],
                    "top_level_record_sequence": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                    "top_level_mtef_xml_tags": [
                        "encoding_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "font_def",
                        "eqn_prefs",
                        "full",
                        "slot",
                        "end",
                    ],
                },
                "neighbor_eqn_prefs_counts": {"sizes_count": 8, "spaces_count": 30, "styles_count": 12},
                "neighbor_effective_suffix_8": "00837a0000000a00",
                "neighbor_effective_suffix_12": "00000a01000200837a000000",
                "neighbor_effective_suffix_16": "01000400000a01000200837a0000000a",
                "neighbor_dispatch_probe": {
                    "next_record": {
                        "name": "slot",
                        "child_records": [{"name": "char"}],
                    },
                    "termination_condition": "CONTINUE_INTO_SLOT",
                },
            }
        ]

        with patch.object(MODULE, "deep_inspect_payload_class", return_value=family_deep):
            report = MODULE.summarize_subtype_specific_poc(
                family_payload_classes,
                neighbor_comparisons,
                runtime={},
                source_input_map={},
            )

        self.assertEqual(report["matched_family_count"], 3)
        self.assertEqual(report["matched_control_count"], 0)
        self.assertEqual(report["trigger_false_positive_controls"], 0)
        self.assertTrue(report["controls_trace_preserved"])
        self.assertEqual(report["additional_parser_stage_evidence_count"], 0)
        self.assertEqual(
            report["interpretive_pivot_summary"]["dominant_family_pivot_labels"],
            {"NO_NEW_PIVOT_BEYOND_FIRST_RECORD_AFTER_FULL": 3},
        )
        self.assertEqual(
            report["interpretive_pivot_summary"]["control_pivot_labels"],
            {"TRIGGER_NOT_MATCHED": 1},
        )
        self.assertFalse(report["interpretive_pivot_summary"]["new_interpretive_pivot_detected"])
        self.assertEqual(
            report["new_interpretation_hypothesis"],
            "No new interpretive pivot was found beyond FIRST_RECORD_AFTER_FULL; the subtype still terminates at END immediately after FULL.",
        )
        self.assertEqual(
            report["family_entries"][0]["interpretive_pivot"]["pivot_label"],
            "NO_NEW_PIVOT_BEYOND_FIRST_RECORD_AFTER_FULL",
        )
        self.assertEqual(
            report["control_entries"][0]["interpretive_pivot"]["pivot_label"],
            "TRIGGER_NOT_MATCHED",
        )
        self.assertEqual(report["final_label"], "NO_ADDITIONAL_EVIDENCE_FROM_POC")
        self.assertFalse(report["open_upstream_production_fix_branch"])

    def test_build_frozen_baseline_summarizes_current_handoff_state(self) -> None:
        payload = {
            "selection": {
                "registry_sources_total": 1,
                "external_sources_total": 2,
                "external_docx_sources_total": 2,
            },
            "family_report": {
                "payload_class_count": 3,
                "occurrence_count": 5,
                "source_family_count": 3,
                "evidence_label": "UNSUPPORTED_SUBTYPE",
                "primary_label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
                "final_label": "UNSUPPORTED_SUBTYPE",
                "structural_subtaxa": [
                    {
                        "subtaxonomy": "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL",
                        "payload_class_count": 3,
                        "occurrence_count": 5,
                        "source_family_count": 3,
                    }
                ],
                "exact_variants": [
                    {
                        "subtaxonomy": "FULL_END_ONLY_CANONICAL_193_194",
                        "payload_class_count": 3,
                        "occurrence_count": 5,
                        "source_family_count": 3,
                    }
                ],
                "stage_assessment": {
                    "label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
                    "first_structural_split_point": "FIRST_RECORD_AFTER_FULL",
                },
                "fingerprint_report": {
                    "final_label": "STRONG_PRE_DISPATCH_FINGERPRINT",
                    "best_candidate": {
                        "key": "composite_pre_dispatch",
                        "coverage": 3,
                        "family_total": 3,
                        "false_positive_controls": 0,
                        "control_total": 3,
                    },
                },
                "subtype_poc_report": {
                    "final_label": "NO_ADDITIONAL_EVIDENCE_FROM_POC",
                },
                "recommendation": {
                    "reason": "Investigate parser input interpretation in a separate upstream branch.",
                    "open_upstream_investigation_branch": True,
                    "open_upstream_production_fix_branch": False,
                },
            },
        }

        baseline = MODULE.build_frozen_baseline(payload)

        self.assertEqual(
            baseline["current_dominant_family_baseline"]["dominant_family"],
            "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL",
        )
        self.assertEqual(baseline["confirmed_findings"]["evidence_label"], "UNSUPPORTED_SUBTYPE")
        self.assertEqual(
            baseline["confirmed_findings"]["action_label"],
            "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
        )
        self.assertEqual(
            baseline["confirmed_findings"]["fingerprint_label"],
            "STRONG_PRE_DISPATCH_FINGERPRINT",
        )
        self.assertEqual(
            baseline["confirmed_findings"]["poc_label"],
            "NO_ADDITIONAL_EVIDENCE_FROM_POC",
        )
        self.assertEqual(
            baseline["current_strongest_trigger"]["trigger_name"],
            "composite_pre_dispatch",
        )
        self.assertEqual(
            baseline["current_strongest_trigger"]["canonical_signature"]["equation_bytes_pair"],
            [193, 194],
        )
        self.assertEqual(
            baseline["current_action_recommendation"]["acceptance_gate"]["dominant_family_still_matches"],
            "3/3",
        )
        self.assertEqual(
            baseline["current_action_recommendation"]["acceptance_gate"]["false_positive_controls_stay"],
            "0/3",
        )
        self.assertIn("Do not open a production fix.", baseline["current_non_goals"])

    def test_emit_frozen_baseline_text_prints_handoff_sections(self) -> None:
        baseline = {
            "current_dominant_family_baseline": {
                "dominant_family": "FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL",
                "payload_class_count": 3,
                "occurrence_count": 5,
                "source_family_count": 3,
                "decision_point": "FIRST_RECORD_AFTER_FULL",
                "decision_point_human": "first record after full",
                "top_level_dispatch_site_human": "NamedRecord/Equation top-level dispatch after full",
                "dominant_path": "full -> end",
                "renderable_controls_path": "full -> slot -> ...",
            },
            "confirmed_findings": {
                "evidence_label": "UNSUPPORTED_SUBTYPE",
                "action_label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
                "fingerprint_label": "STRONG_PRE_DISPATCH_FINGERPRINT",
                "poc_label": "NO_ADDITIONAL_EVIDENCE_FROM_POC",
            },
            "current_strongest_trigger": {
                "trigger_name": "composite_pre_dispatch",
                "coverage": "3/3",
                "false_positive_controls": "0/3",
                "canonical_signature": {
                    "equation_bytes_pair": [193, 194],
                },
            },
            "current_action_recommendation": {
                "action_label": "INVESTIGATE_PARSER_INPUT_INTERPRETATION",
                "follow_up_branch_suggestion": "upstream parser input interpretation investigation branch",
                "recommendation": "Keep this as an investigation-only baseline.",
                "acceptance_gate": {
                    "dominant_family_still_matches": "3/3",
                    "false_positive_controls_stay": "0/3",
                    "controls_preserve_renderable_path": "full -> slot -> ...",
                    "only_accept_if_new_parser_stage_body_evidence_appears": True,
                },
            },
            "current_non_goals": [
                "Do not open a production fix.",
            ],
            "handoff_answers": {
                "current_baseline_frozen_clearly": True,
            },
        }

        out = io.StringIO()
        with redirect_stdout(out):
            MODULE.emit_frozen_baseline_text(baseline)
        text = out.getvalue()

        self.assertIn("Current DSMT4 investigation baseline:", text)
        self.assertIn("current_dominant_family_baseline=FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL", text)
        self.assertIn("current_strongest_trigger=composite_pre_dispatch", text)
        self.assertIn("Current non-goals:", text)
        self.assertIn("Handoff answers:", text)


if __name__ == "__main__":
    unittest.main()
