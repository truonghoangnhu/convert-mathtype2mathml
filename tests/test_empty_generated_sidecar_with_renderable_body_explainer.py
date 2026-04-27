from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "explain_empty_generated_sidecar_with_renderable_body.py"
SPEC = importlib.util.spec_from_file_location("explain_empty_generated_sidecar_with_renderable_body", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EmptyGeneratedSidecarWithRenderableBodyExplainerTest(unittest.TestCase):
    def test_renderable_body_tag_counts_excludes_mt_comment_tags(self) -> None:
        summary = {
            "body_tag_counts": {
                "mt_comment": 1,
                "comment_length": 1,
                "comment_type": 1,
                "comment_data": 1,
                "line": 2,
            }
        }

        counts = MODULE.renderable_body_tag_counts(summary)

        self.assertEqual(counts, {"line": 2})

    def test_classify_stage_level_root_cause_marks_comment_only_case_as_classification_boundary(self) -> None:
        entry = {
            "deep_audit": {
                "bin_mtef_summary": {
                    "body_tag_counts": {
                        "mt_comment": 1,
                        "comment_length": 1,
                        "comment_type": 1,
                        "comment_data": 1,
                    }
                },
                "preview_mtef_summary": {
                    "body_tag_counts": {
                        "mt_comment": 1,
                    }
                },
                "bin_parser": {
                    "top_level_records": [
                        {"name": "mt_comment"},
                        {"name": "encoding_def"},
                        {"name": "full"},
                        {"name": "end"},
                    ]
                },
                "preview_parser": {
                    "top_level_records": [
                        {"name": "mt_comment"},
                        {"name": "encoding_def"},
                        {"name": "full"},
                        {"name": "end"},
                    ]
                },
            }
        }

        diagnosis = MODULE.classify_stage_level_root_cause(entry)

        self.assertEqual(diagnosis["diagnosis"], "CLASSIFICATION_BOUNDARY_AROUND_MT_COMMENT")
        self.assertFalse(diagnosis["renderable_body_evidence_before_mathml"])
        self.assertTrue(diagnosis["mt_comment_prefix_present"])
        self.assertEqual(diagnosis["renderable_body_status"], "COMMENT_ARTIFACT_ONLY")
        self.assertTrue(diagnosis["comment_artifact_only"])
        self.assertEqual(
            diagnosis["comment_artifact_tag_counts"],
            {
                "bin": {
                    "comment_data": 1,
                    "comment_length": 1,
                    "comment_type": 1,
                    "mt_comment": 1,
                },
                "preview": {
                    "mt_comment": 1,
                },
            },
        )

    def test_summarize_target_family_keeps_investigation_at_converter_boundary_without_fix_branch(self) -> None:
        target_classes = [
            {
                "source_names": ["external-workdir:work/dsmt4-external-audit/10-toan-hcm-2026--5c97b34e92a9"],
                "source_families": ["10-toan-hcm-2026--5c97b34e92a9"],
                "occurrence_count": 1,
                "class_key": "abc|def",
                "ole_parts": ["/word/embeddings/oleObject3009.bin"],
                "preview_parts": ["/word/media/image2537.wmf"],
                "pattern_stage": "CONVERTER_INVESTIGATION",
                "pattern_signature": {
                    "bin_parser_class": "Mathtype::OleFileParser",
                    "preview_parser_class": "Mathtype::WmfFileParser",
                    "bin_equation_bytes": 216,
                    "preview_equation_bytes": 217,
                    "bin_top_level_record_sequence": ["mt_comment", "encoding_def", "eqn_prefs", "full", "end"],
                    "bin_tail_after_eqn_prefs": ["full", "end"],
                    "bin_sidecar_status": "missing",
                    "preview_sidecar_status": "empty_math",
                    "same_effective_payload": True,
                },
                "assessment": {
                    "decision": "INVESTIGATE_TRANSPECT_CONVERTER",
                    "reason": "Could not prove a downstream filtering bug; upstream conversion still needs inspection.",
                },
                "deep_audit": {
                    "bin_mtef_summary": {
                        "body_tag_counts": {
                            "mt_comment": 1,
                            "comment_length": 1,
                        }
                    },
                    "preview_mtef_summary": {
                        "body_tag_counts": {
                            "mt_comment": 1,
                        }
                    },
                    "bin_parser": {
                        "top_level_records": [
                            {"name": "mt_comment"},
                            {"name": "encoding_def"},
                            {"name": "eqn_prefs"},
                            {"name": "full"},
                            {"name": "end"},
                        ]
                    },
                    "preview_parser": {
                        "top_level_records": [
                            {"name": "mt_comment"},
                            {"name": "encoding_def"},
                            {"name": "eqn_prefs"},
                            {"name": "full"},
                            {"name": "end"},
                        ]
                    },
                },
            }
        ]

        summary = MODULE.summarize_target_family(target_classes)

        self.assertEqual(summary["family"], "EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY")
        self.assertEqual(summary["occurrences"], 1)
        self.assertEqual(summary["payload_classes"], 1)
        self.assertEqual(summary["final_label"], "INVESTIGATE_TRANSPECT_CONVERTER")
        self.assertFalse(summary["open_production_fix_branch"])
        self.assertEqual(summary["target_stage_if_reopened"], "CONVERTER_CLASSIFICATION_BOUNDARY")
        self.assertEqual(
            summary["entries"][0]["source_parts"],
            {
                "ole_parts": ["/word/embeddings/oleObject3009.bin"],
                "preview_parts": ["/word/media/image2537.wmf"],
            },
        )
        self.assertEqual(summary["entries"][0]["main_signature"]["bin_sidecar_status"], "missing")


if __name__ == "__main__":
    unittest.main()
