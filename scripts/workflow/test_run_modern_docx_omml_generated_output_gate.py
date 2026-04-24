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
    def test_renders_compact_omml_attention_for_attention_worthy_case(self) -> None:
        report = {
            "case_count": 1,
            "drift_candidate_count": 1,
            "drift_class_counts": {
                "no_drift": 0,
                "serializer_only_drift": 0,
                "structural_drift": 1,
            },
            "cases": [
                {
                    "case_id": "case-a",
                    "drift_class": "structural_drift",
                    "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                    "patch_summary_record": {
                        "omml_preservation": "drift_unexpected:eq|block|shape",
                        "omml_drift_class": "unexpected_native_drift",
                        "omml_drift_warning": "eq|block|shape",
                    },
                }
            ],
        }
        rendered = render_patch_path_diagnostics_summary(report)
        self.assertIn("Patch-path OMML attention:", rendered)
        self.assertIn(
            "- case-a: omml_attention preservation=drift_unexpected:eq|block|shape "
            "drift_class=unexpected_native_drift drift_warning=eq|block|shape",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()

