from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "explain_empty_generated_sidecar.py"
SPEC = importlib.util.spec_from_file_location("explain_empty_generated_sidecar", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EmptyGeneratedSidecarExplainerTest(unittest.TestCase):
    def test_summarize_mtef_xml_marks_metadata_only(self) -> None:
        xml_text = """<?xml version="1.0"?>
<root>
  <mtef>
    <mtef_version>5</mtef_version>
    <application_key>DSMT7</application_key>
    <equation_options>inline</equation_options>
    <eqn_prefs><options>0</options></eqn_prefs>
    <full/>
    <end/>
  </mtef>
</root>
"""

        summary = MODULE.summarize_mtef_xml(xml_text)

        self.assertTrue(summary["metadata_only"])
        self.assertEqual(summary["body_tag_counts"], {})
        self.assertEqual(summary["application_key"], "DSMT7")
        self.assertEqual(summary["equation_options"], "inline")
        self.assertEqual(summary["tail_after_eqn_prefs"], ["full", "end"])

    def test_summarize_mtef_xml_detects_body_tags(self) -> None:
        xml_text = """<?xml version="1.0"?>
<root>
  <mtef>
    <mtef_version>5</mtef_version>
    <application_key>DSMT7</application_key>
    <line>
      <char>
        <mt_code_value>123</mt_code_value>
      </char>
    </line>
    <end/>
  </mtef>
</root>
"""

        summary = MODULE.summarize_mtef_xml(xml_text)

        self.assertFalse(summary["metadata_only"])
        self.assertEqual(summary["body_tag_counts"]["line"], 1)
        self.assertEqual(summary["body_tag_counts"]["char"], 1)
        self.assertEqual(summary["tail_after_eqn_prefs"], ["mtef_version", "application_key", "line", "end"])

    def test_compare_equation_payloads_treats_trailing_preview_byte_as_same_effective_payload(self) -> None:
        bin_parser = {"equation_hex": "0102030a00"}
        preview_parser = {"equation_hex": "0102030a000a"}

        comparison = MODULE.compare_equation_payloads(bin_parser, preview_parser)

        self.assertFalse(comparison["exact_match"])
        self.assertTrue(comparison["same_effective_payload"])
        self.assertEqual(comparison["shared_prefix_bytes"], 5)
        self.assertEqual(comparison["preview_trailing_hex"], "0a")

    def test_assess_group_marks_unsupported_or_degenerate_payload_for_full_end_only(self) -> None:
        metadata_only = {
            "metadata_only": True,
            "body_tag_counts": {},
            "tail_after_eqn_prefs": ["full", "end"],
        }
        parser = {
            "top_level_records": [
                {"name": "encoding_def"},
                {"name": "font_def"},
                {"name": "eqn_prefs"},
                {"name": "full"},
                {"name": "end"},
            ]
        }
        payload_comparison = {
            "same_effective_payload": True,
            "shared_prefix_bytes": 193,
        }

        assessment = MODULE.assess_group(
            bin_summary=metadata_only,
            preview_summary=metadata_only,
            bin_parser=parser,
            preview_parser=parser,
            bin_sidecar_status="empty_math",
            preview_sidecar_status="empty_math",
            payload_comparison=payload_comparison,
        )

        self.assertEqual(assessment["result"], "TOP_LEVEL_FULL_END_ONLY")
        self.assertEqual(assessment["decision"], "UNSUPPORTED_OR_DEGENERATE_PAYLOAD")
        self.assertEqual(assessment["stage"], "PARSER_INPUT_PAYLOAD")

    def test_assess_group_prefers_mtef_to_mathml_fix_when_body_present(self) -> None:
        bin_summary = {
            "metadata_only": False,
            "body_tag_counts": {"line": 1},
            "tail_after_eqn_prefs": ["line", "end"],
        }
        preview_summary = {
            "metadata_only": True,
            "body_tag_counts": {},
            "tail_after_eqn_prefs": ["full", "end"],
        }
        parser = {"top_level_records": [{"name": "line"}]}

        assessment = MODULE.assess_group(
            bin_summary=bin_summary,
            preview_summary=preview_summary,
            bin_parser=parser,
            preview_parser=parser,
            bin_sidecar_status="empty_math",
            preview_sidecar_status="empty_math",
            payload_comparison={"same_effective_payload": False},
        )

        self.assertEqual(assessment["result"], "BODY_PRESENT_BUT_EMPTY_MATHML")
        self.assertEqual(assessment["decision"], "FIX_MTEF_TO_MATHML_STAGE")
        self.assertEqual(assessment["stage"], "MTEF_TO_MATHML_STAGE")


if __name__ == "__main__":
    unittest.main()
