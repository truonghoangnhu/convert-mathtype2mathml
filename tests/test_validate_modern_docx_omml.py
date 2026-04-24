from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.workflow.run_modern_docx_omml_smoke import main as run_modern_docx_omml_smoke
from scripts.workflow.validate_modern_docx_omml import DEFAULT_INVENTORY, inspect_docx, validate_inventory


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _write_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("word/document.xml", document_xml)


class ModernDocxOmmlValidatorTests(unittest.TestCase):
    def test_inspect_docx_counts_inline_and_block_omml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "sample.docx"
            _write_docx(
                docx_path,
                f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:r>
    </w:p>
    <w:p>
      <m:oMathPara><m:oMath><m:r><m:t>y</m:t></m:r></m:oMath></m:oMathPara>
    </w:p>
  </w:body>
</w:document>
""",
            )

            result = inspect_docx(docx_path)

            self.assertTrue(result["document_xml_exists"])
            self.assertTrue(result["document_xml_parseable"])
            self.assertEqual(result["omath_count"], 2)
            self.assertEqual(result["omathpara_count"], 1)
            self.assertTrue(result["appears_inline_math"])
            self.assertTrue(result["appears_block_math"])
            self.assertTrue(result["basic_omml_structure_present"])

    def test_validate_inventory_skips_placeholder_and_passes_real_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docx_path = tmp_path / "inline.docx"
            inventory_path = tmp_path / "inventory.json"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body><w:p><w:r><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:r></w:p></w:body>
</w:document>
""",
            )
            inventory_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "placeholder",
                                "source_docx": "TODO",
                                "classification": "supported",
                            },
                            {
                                "case_id": "inline",
                                "source_docx": "inline.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 1,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 1,
                                },
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = validate_inventory(inventory_path)

            self.assertEqual(report["case_count"], 2)
            self.assertEqual(report["passed_count"], 1)
            self.assertEqual(report["expected_failed_count"], 0)
            self.assertEqual(report["unexpected_failed_count"], 0)
            self.assertEqual(report["skipped_count"], 1)
            self.assertEqual(report["failed_count"], 0)

    def test_default_inventory_summary_distinguishes_expected_failure(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)

        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["passed_count"], 4)
        self.assertEqual(report["expected_failed_count"], 1)
        self.assertEqual(report["unexpected_failed_count"], 0)
        self.assertEqual(report["skipped_count"], 0)
        self.assertEqual(report["failed_count"], 1)

    def test_default_inventory_locks_first_real_modern_omml_case(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)
        case = next(item for item in report["cases"] if item["case_id"] == "modern_mixed_block_inline_sample")
        inspection = case["inspection"]

        self.assertEqual(case["status"], "passed")
        self.assertIsInstance(inspection, dict)
        self.assertTrue(inspection["document_xml_exists"])
        self.assertTrue(inspection["document_xml_parseable"])
        self.assertEqual(inspection["omath_count"], 2)
        self.assertEqual(inspection["omathpara_count"], 1)
        self.assertEqual(inspection["inline_omath_count"], 1)
        self.assertTrue(inspection["appears_inline_math"])
        self.assertTrue(inspection["appears_block_math"])
        self.assertTrue(inspection["basic_omml_structure_present"])

    def test_default_inventory_locks_inline_only_modern_omml_case(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)
        case = next(item for item in report["cases"] if item["case_id"] == "modern_inline_omml_sample")
        inspection = case["inspection"]

        self.assertEqual(case["status"], "passed")
        self.assertIsInstance(inspection, dict)
        self.assertTrue(inspection["document_xml_exists"])
        self.assertTrue(inspection["document_xml_parseable"])
        self.assertEqual(inspection["omath_count"], 1)
        self.assertEqual(inspection["omathpara_count"], 0)
        self.assertEqual(inspection["inline_omath_count"], 1)
        self.assertTrue(inspection["appears_inline_math"])
        self.assertFalse(inspection["appears_block_math"])
        self.assertTrue(inspection["basic_omml_structure_present"])

    def test_default_inventory_locks_block_only_modern_omml_case(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)
        case = next(item for item in report["cases"] if item["case_id"] == "modern_block_omml_sample")
        inspection = case["inspection"]

        self.assertEqual(case["status"], "passed")
        self.assertIsInstance(inspection, dict)
        self.assertTrue(inspection["document_xml_exists"])
        self.assertTrue(inspection["document_xml_parseable"])
        self.assertEqual(inspection["omath_count"], 1)
        self.assertEqual(inspection["omathpara_count"], 1)
        self.assertEqual(inspection["inline_omath_count"], 0)
        self.assertFalse(inspection["appears_inline_math"])
        self.assertTrue(inspection["appears_block_math"])
        self.assertTrue(inspection["basic_omml_structure_present"])

    def test_default_inventory_locks_multi_equation_paragraph_case(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)
        case = next(item for item in report["cases"] if item["case_id"] == "modern_supported_multi_equation_paragraph")
        inspection = case["inspection"]

        self.assertEqual(case["status"], "passed")
        self.assertIsInstance(inspection, dict)
        self.assertTrue(inspection["document_xml_exists"])
        self.assertTrue(inspection["document_xml_parseable"])
        self.assertEqual(inspection["omath_count"], 2)
        self.assertEqual(inspection["omathpara_count"], 0)
        self.assertEqual(inspection["inline_omath_count"], 2)
        self.assertTrue(inspection["appears_inline_math"])
        self.assertFalse(inspection["appears_block_math"])
        self.assertTrue(inspection["basic_omml_structure_present"])

    def test_default_inventory_locks_negative_malformed_docx_case(self) -> None:
        report = validate_inventory(DEFAULT_INVENTORY)
        case = next(item for item in report["cases"] if item["case_id"] == "modern_negative_malformed_or_unsupported_package")
        inspection = case["inspection"]

        self.assertEqual(case["status"], "failed")
        self.assertEqual(case["expected_status"], "failed")
        self.assertEqual(case["result"], "expected_failed")
        self.assertIsInstance(inspection, dict)
        self.assertTrue(inspection["document_xml_exists"])
        self.assertFalse(inspection["document_xml_parseable"])
        self.assertEqual(inspection["omath_count"], 0)
        self.assertEqual(inspection["omathpara_count"], 0)
        self.assertEqual(inspection["inline_omath_count"], 0)
        self.assertFalse(inspection["appears_inline_math"])
        self.assertFalse(inspection["appears_block_math"])
        self.assertFalse(inspection["basic_omml_structure_present"])
        self.assertTrue(any("not parseable XML" in failure for failure in case["failures"]))

    def test_named_smoke_entrypoint_reports_bucket_summary_and_exits_zero(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = run_modern_docx_omml_smoke([])

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Modern DOCX + OMML validation", rendered)
        self.assertIn("regression_set/modern_docx_omml_inventory.json", rendered)
        self.assertIn("passed=4", rendered)
        self.assertIn("expected_failed=1", rendered)
        self.assertIn("unexpected_failed=0", rendered)
        self.assertIn("skipped=0", rendered)


if __name__ == "__main__":
    unittest.main()
