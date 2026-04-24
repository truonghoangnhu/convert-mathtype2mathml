#!/usr/bin/env python3
from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow.render_modern_docx_omml_gate_summary import render_summary_markdown


class RenderModernDocxOmmlGateSummaryTest(unittest.TestCase):
    def test_surfaces_compact_omml_attention_signal_for_attention_worthy_case(self) -> None:
        report = {
            "overall_gate_result": "failed",
            "structural_summary": {
                "case_count": 1,
                "passed_count": 0,
                "expected_failed_count": 0,
                "unexpected_failed_count": 1,
                "skipped_count": 0,
                "structural_failed_check_count": 1,
            },
            "case_statuses": [
                {
                    "case_id": "case-a",
                    "gate_status": "failed",
                    "structural_status": "failed",
                }
            ],
            "structural_diffs": [],
            "patch_path_diagnostics": {
                "cases": [
                    {
                        "case_id": "case-a",
                        "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                        "drift_class": "structural_drift",
                        "patch_summary_record": {
                            "omml_preservation": "drift_unexpected:eq|block|shape",
                            "omml_drift_class": "unexpected_native_drift",
                            "omml_drift_warning": "eq|block|shape",
                        },
                    }
                ]
            },
        }

        markdown = render_summary_markdown(report)
        self.assertIn(
            "- omml_attention: `preservation=drift_unexpected:eq|block|shape "
            "drift_class=unexpected_native_drift drift_warning=eq|block|shape`",
            markdown,
        )

    def test_omml_attention_line_is_omitted_when_no_signal_fields_present(self) -> None:
        report = {
            "overall_gate_result": "failed",
            "structural_summary": {
                "case_count": 1,
                "passed_count": 0,
                "expected_failed_count": 0,
                "unexpected_failed_count": 1,
                "skipped_count": 0,
                "structural_failed_check_count": 1,
            },
            "case_statuses": [
                {
                    "case_id": "case-b",
                    "gate_status": "failed",
                    "structural_status": "failed",
                }
            ],
            "structural_diffs": [],
            "patch_path_diagnostics": {
                "cases": [
                    {
                        "case_id": "case-b",
                        "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                        "drift_class": "structural_drift",
                        "patch_summary_record": {
                            "omml_before": "eq:1,inline:1,block:0,shape:inline_only",
                            "omml_after": "eq:1,inline:1,block:0,shape:inline_only",
                        },
                    }
                ]
            },
        }

        markdown = render_summary_markdown(report)
        self.assertNotIn("- omml_attention:", markdown)


if __name__ == "__main__":
    unittest.main()
