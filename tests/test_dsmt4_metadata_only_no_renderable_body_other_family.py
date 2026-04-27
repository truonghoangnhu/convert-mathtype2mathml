from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "explain_dsmt4_metadata_only_no_renderable_body_other_family.py"
SPEC = importlib.util.spec_from_file_location("explain_dsmt4_metadata_only_no_renderable_body_other_family", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def family_entry(
    *,
    source_name: str,
    source_family: str,
    occurrence_count: int,
    bytes_pair: tuple[int, int],
    checksums: tuple[str, str],
) -> dict:
    return {
        "source_names": [source_name],
        "source_families": [source_family],
        "occurrence_count": occurrence_count,
        "class_key": f"{checksums[0]}|{checksums[1]}",
        "pattern_signature": {
            "stage": "PARSER_STAGE",
            "assessment_result": "METADATA_ONLY_MTEF_XML",
            "assessment_decision": "INVESTIGATE_TRANSPECT_CONVERTER",
            "same_effective_payload": True,
            "bin_sidecar_status": "missing",
            "preview_sidecar_status": "empty_math",
            "bin_parser_class": "Mathtype::OleFileParser",
            "preview_parser_class": "Mathtype::WmfFileParser",
            "bin_equation_bytes": bytes_pair[0],
            "preview_equation_bytes": bytes_pair[1],
            "bin_checksum": checksums[0],
            "preview_checksum": checksums[1],
            "bin_top_level_record_sequence": [
                "encoding_def",
                "font_def",
                "font_def",
                "font_def",
                "font_def",
                "eqn_prefs",
                "full",
                "end",
            ],
            "bin_tail_after_eqn_prefs": ["full", "end"],
        },
        "assessment": {
            "result": "METADATA_ONLY_MTEF_XML",
            "decision": "INVESTIGATE_TRANSPECT_CONVERTER",
        },
    }


def full_end_entry(*, source_name: str, bytes_pair: tuple[int, int]) -> dict:
    return {
        "source_names": [source_name],
        "pattern_signature": {
            "bin_equation_bytes": bytes_pair[0],
            "preview_equation_bytes": bytes_pair[1],
            "bin_top_level_record_sequence": [
                "encoding_def",
                "font_def",
                "font_def",
                "font_def",
                "font_def",
                "eqn_prefs",
                "full",
                "end",
            ],
            "bin_tail_after_eqn_prefs": ["full", "end"],
        },
    }


class Dsmt4MetadataOnlyNoRenderableBodyOtherFamilyTest(unittest.TestCase):
    def test_summarize_target_family_marks_single_structural_signature_as_canonical(self) -> None:
        entries = [
            family_entry(
                source_name="external-docx:in/_Hoa_2026_Big.docx",
                source_family="_Hoa_2026_Big",
                occurrence_count=2,
                bytes_pair=(193, 194),
                checksums=("35F3", "35FD"),
            ),
            family_entry(
                source_name="external-docx:in/_Toan_2026_Big.docx",
                source_family="_Toan_2026_Big",
                occurrence_count=1,
                bytes_pair=(198, 199),
                checksums=("3820", "3820"),
            ),
        ]

        summary = MODULE.summarize_target_family(entries, [])

        self.assertTrue(summary["canonical_signature"]["present"])
        self.assertEqual(summary["dominant_signature"]["dominant_bytes_pair"], [193, 194])
        self.assertEqual(summary["decision_label"], "KEEP_TAXONOMY_ONLY_NEAR_FULL_END_ONLY")
        self.assertFalse(summary["open_investigation_branch"])

    def test_relation_to_full_end_only_marks_same_source_exact_shape_as_near_variant(self) -> None:
        entry = family_entry(
            source_name="external-docx:in/_Toan_2026_Big.docx",
            source_family="_Toan_2026_Big",
            occurrence_count=1,
            bytes_pair=(193, 194),
            checksums=("35F3", "35FD"),
        )
        full_entry = full_end_entry(
            source_name="external-docx:in/_Toan_2026_Big.docx",
            bytes_pair=(193, 194),
        )

        relation = MODULE.relation_to_full_end_only(entry, [full_entry])

        self.assertEqual(
            relation,
            "Same-source near-variant of FULL_END_ONLY with matching canonical shape and matching bytes pair.",
        )

    def test_deep_audit_table_groups_rows_by_source(self) -> None:
        entries = [
            family_entry(
                source_name="external-docx:in/_Hoa_2026_Big.docx",
                source_family="_Hoa_2026_Big",
                occurrence_count=2,
                bytes_pair=(193, 194),
                checksums=("35F3", "35FD"),
            ),
            family_entry(
                source_name="external-docx:in/_Hoa_2026_Big.docx",
                source_family="_Hoa_2026_Big",
                occurrence_count=1,
                bytes_pair=(193, 194),
                checksums=("35F4", "35FE"),
            ),
        ]

        summary = MODULE.summarize_target_family(entries, [])

        self.assertEqual(len(summary["deep_audit_table"]), 1)
        self.assertEqual(summary["deep_audit_table"][0]["occurrences"], 3)
        self.assertEqual(summary["deep_audit_table"][0]["payload_classes"], 2)


if __name__ == "__main__":
    unittest.main()
