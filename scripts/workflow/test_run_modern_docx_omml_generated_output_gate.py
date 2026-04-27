#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.run_modern_docx_omml_generated_output_gate import render_patch_path_diagnostics_summary


class RunModernDocxOmmlGeneratedOutputGateTest(unittest.TestCase):
    def test_renders_compact_attention_split_and_stable_ordering(self) -> None:
        report = {
            "case_count": 2,
            "drift_candidate_count": 2,
            "drift_class_counts": {
                "no_drift": 0,
                "serializer_only_drift": 0,
                "structural_drift": 2,
            },
            "cases": [
                {
                    "case_id": "case-b",
                    "drift_class": "structural_drift",
                    "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                    "patch_summary_record": {
                        "omml_preservation": "drift_expected:eq|block|shape",
                        "omml_drift_class": "expected_patch_drift",
                        "omml_drift_warning": "eq|block|shape",
                    },
                },
                {
                    "case_id": "case-a",
                    "drift_class": "structural_drift",
                    "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                    "patch_summary_record": {
                        "omml_preservation": "drift_unexpected:eq|block|shape",
                        "omml_drift_class": "unexpected_native_drift",
                        "omml_drift_warning": "eq|block|shape",
                    },
                },
            ],
        }
        rendered = render_patch_path_diagnostics_summary(report)
        lines = rendered.splitlines()
        self.assertEqual(
            "Patch-path diagnostics: cases=2 drift_candidates=2 serializer_only=0 "
            "attention_cases=2 attention_expected=1 attention_unexpected=1",
            lines[0],
        )
        self.assertEqual("Patch-path attention case_ids: case-a,case-b", lines[1])
        self.assertEqual("Patch-path OMML attention:", lines[4])
        self.assertEqual(
            "- case-a: omml_attention preservation=drift_unexpected:eq|block|shape "
            "drift_class=unexpected_native_drift drift_warning=eq|block|shape",
            lines[5],
        )
        self.assertEqual(
            "- case-b: omml_attention preservation=drift_expected:eq|block|shape "
            "drift_class=expected_patch_drift drift_warning=eq|block|shape",
            lines[6],
        )

    def test_keeps_no_attention_summary_short(self) -> None:
        report = {
            "case_count": 1,
            "drift_candidate_count": 0,
            "drift_class_counts": {
                "no_drift": 1,
                "serializer_only_drift": 0,
                "structural_drift": 0,
            },
            "cases": [
                {
                    "case_id": "case-z",
                    "drift_class": "no_drift",
                    "drift_origin_hint": "no_structural_drift_detected",
                    "patch_summary_record": {
                        "omml_preservation": "preserved",
                    },
                }
            ],
        }
        rendered = render_patch_path_diagnostics_summary(report)
        self.assertEqual(
            "Patch-path diagnostics: cases=1 drift_candidates=0 serializer_only=0 "
            "attention_cases=0 attention_expected=0 attention_unexpected=0",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
