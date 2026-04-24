from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.workflow.generate_modern_docx_omml_output_manifest import DEFAULT_CASE_IDS, build_manifest_case
from scripts.workflow.run_modern_docx_omml_generated_output_gate import (
    check_docx_openability,
    main as run_generated_output_gate,
)
from scripts.workflow.run_modern_docx_omml_smoke import main as run_modern_docx_omml_smoke
from scripts.workflow.validate_modern_docx_omml import (
    DEFAULT_INVENTORY,
    build_structural_checks,
    inspect_docx,
    validate_inventory,
)
from scripts.workflow.validate_modern_docx_omml_structure import main as validate_modern_docx_omml_structure


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _write_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("word/document.xml", document_xml)


def _write_minimal_reopenable_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        docx.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
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
            self.assertTrue(result["basic_omml_structure_valid"])
            self.assertEqual(result["placement_summary"], "mixed inline/block OMML: inline_oMath=1 oMathPara=1")

    def test_structural_checks_report_actual_and_expected_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "sample.docx"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body><w:p><w:r><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:r></w:p></w:body>
</w:document>
""",
            )
            inspection = inspect_docx(docx_path)

            checks = build_structural_checks(
                {
                    "expected": {
                        "document_xml_exists": True,
                        "document_xml_parseable": True,
                        "equation_count": 1,
                        "block_equation_count": 0,
                        "inline_equation_count": 1,
                        "appears_inline_math": True,
                        "appears_block_math": False,
                        "computed_placement_summary": "inline OMML only: inline_oMath=1",
                        "valid_omath_omathpara_structure": True,
                    }
                },
                inspection,
            )

            self.assertTrue(all(check["passed"] for check in checks))
            by_name = {check["name"]: check for check in checks}
            self.assertEqual(by_name["omath_count"]["actual"], 1)
            self.assertEqual(by_name["omath_count"]["expected"], 1)
            self.assertEqual(by_name["placement_summary"]["actual"], "inline OMML only: inline_oMath=1")
            self.assertEqual(by_name["placement_summary"]["expected"], "inline OMML only: inline_oMath=1")

    def test_inventory_can_validate_generated_output_docx_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_docx_path = tmp_path / "source.docx"
            output_docx_path = tmp_path / "generated.docx"
            inventory_path = tmp_path / "inventory.json"
            _write_docx(
                source_docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body><w:p><m:oMathPara><m:oMath><m:r><m:t>y</m:t></m:r></m:oMath></m:oMathPara></w:p></w:body>
</w:document>
""",
            )
            _write_docx(
                output_docx_path,
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
                                "case_id": "generated-inline",
                                "source_docx": "source.docx",
                                "output_docx": "generated.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 1,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 1,
                                    "appears_inline_math": True,
                                    "appears_block_math": False,
                                    "valid_omath_omathpara_structure": True,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = validate_inventory(inventory_path)
            case = report["cases"][0]

            self.assertEqual(case["result"], "passed")
            self.assertEqual(case["target_docx"], "generated.docx")
            self.assertTrue(str(case["inspection"]["file_path"]).endswith("generated.docx"))

    def test_generated_output_manifest_case_records_structural_expectations(self) -> None:
        manifest_case = build_manifest_case(
            {
                "case_id": "modern_inline_omml_sample",
                "source_docx": "samples/sample-inline-omml.docx",
                "expected": {
                    "equation_count": 1,
                    "block_equation_count": 0,
                    "inline_equation_count": 1,
                },
            },
            Path("modern_inline_omml_sample.generated.docx"),
        )

        self.assertEqual(manifest_case["case_id"], "modern_inline_omml_sample_generated_output")
        self.assertEqual(manifest_case["generated_docx"], "modern_inline_omml_sample.generated.docx")
        expected = manifest_case["expected"]
        self.assertEqual(expected["equation_count"], 1)
        self.assertEqual(expected["block_equation_count"], 0)
        self.assertEqual(expected["inline_equation_count"], 1)
        self.assertTrue(expected["appears_inline_math"])
        self.assertFalse(expected["appears_block_math"])
        self.assertEqual(expected["computed_placement_summary"], "inline OMML only: inline_oMath=1")
        self.assertTrue(expected["valid_omath_omathpara_structure"])

    def test_generated_output_manifest_defaults_cover_four_positive_modern_cases(self) -> None:
        self.assertEqual(
            DEFAULT_CASE_IDS,
            [
                "modern_inline_omml_sample",
                "modern_block_omml_sample",
                "modern_mixed_block_inline_sample",
                "modern_supported_multi_equation_paragraph",
            ],
        )

    def test_openability_check_validates_minimal_docx_package_parts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "generated.docx"
            _write_minimal_reopenable_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body><w:p><w:r><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:r></w:p></w:body>
</w:document>
""",
            )

            result = check_docx_openability(docx_path)

            self.assertTrue(result["passed"])
            self.assertTrue(result["zip_package"])
            self.assertTrue(result["content_types"])
            self.assertTrue(result["root_relationships"])
            self.assertTrue(result["document_xml"])
            self.assertTrue(result["document_xml_parseable"])

    def test_openability_check_fails_when_required_package_part_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "generated.docx"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body><w:p><w:r><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:r></w:p></w:body>
</w:document>
""",
            )

            result = check_docx_openability(docx_path)

            self.assertFalse(result["passed"])
            self.assertIn("[Content_Types].xml missing", result["failures"])
            self.assertIn("_rels/.rels missing", result["failures"])

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

    def test_structural_entrypoint_reports_expected_and_actual_checks(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = validate_modern_docx_omml_structure([])

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Modern DOCX + OMML structural validation", rendered)
        self.assertIn("structural_failed_checks=0", rendered)
        self.assertIn("actual_counts:", rendered)
        self.assertIn("check omath_count: pass", rendered)
        self.assertIn("check basic_omml_structure_valid: pass", rendered)

    def test_structural_entrypoint_fails_on_structural_check_mismatch(self) -> None:
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
                                "case_id": "inline",
                                "source_docx": "inline.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 1,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 1,
                                    "computed_placement_summary": "block OMML only: oMathPara=1",
                                    "valid_omath_omathpara_structure": True,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = validate_modern_docx_omml_structure(["--inventory", str(inventory_path)])

            self.assertEqual(exit_code, 1)
            rendered = output.getvalue()
            self.assertIn("structural_failed_checks=1", rendered)
            self.assertIn("check placement_summary: fail", rendered)

    def test_generated_output_gate_runs_generation_then_structural_validation(self) -> None:
        calls = []

        def fake_generate(argv):
            calls.append(("generate", list(argv)))
            return 0

        def fake_openability(manifest_path):
            calls.append(("openability", [str(manifest_path)]))
            return {"case_count": 4, "passed_count": 4, "failed_count": 0, "results": []}

        def fake_validate(argv):
            calls.append(("validate", list(argv)))
            print("Summary: cases=4 passed=4 expected_failed=0 unexpected_failed=0 skipped=0 structural_failed_checks=0")
            return 0

        output = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "modern_docx_omml_generated_output_gate_report.json"
            manifest_path = Path(tmp) / "modern_docx_omml_generated_outputs.json"
            manifest_path.write_text(json.dumps({"cases": []}), encoding="utf-8")
            with (
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate.GENERATED_GATE_REPORT",
                    report_path,
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate.GENERATED_MANIFEST",
                    manifest_path,
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate.generate_manifest_main",
                    fake_generate,
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_generated_openability",
                    fake_openability,
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_structure_main",
                    fake_validate,
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate._build_structural_report",
                    lambda _: {
                        "case_count": 4,
                        "passed_count": 4,
                        "expected_failed_count": 0,
                        "unexpected_failed_count": 0,
                        "skipped_count": 0,
                        "structural_failed_check_count": 0,
                        "cases": [
                            {"case_id": "case-a", "result": "passed"},
                            {"case_id": "case-b", "result": "passed"},
                        ],
                    },
                ),
                redirect_stdout(output),
            ):
                exit_code = run_generated_output_gate([])

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls[0], ("generate", []))
        self.assertEqual(calls[1][0], "openability")
        self.assertEqual(calls[2][0], "validate")
        self.assertIn("--inventory", calls[2][1])
        rendered = output.getvalue()
        self.assertIn("Modern DOCX + OMML generated-output gate", rendered)
        self.assertIn("Generation: passed", rendered)
        self.assertIn("Openability: cases=4 passed=4 failed=0", rendered)
        self.assertIn("Openability validation: passed", rendered)
        self.assertIn("Summary: cases=4 passed=4", rendered)
        self.assertIn("Structural validation: passed", rendered)
        self.assertEqual(report["manifest_path"], str(manifest_path))
        self.assertEqual(report["generation_result"], "passed")
        self.assertEqual(report["openability_summary"]["status"], "passed")
        self.assertEqual(report["structural_summary"]["status"], "passed")
        self.assertEqual(report["overall_gate_result"], "passed")
        self.assertEqual(report["case_statuses"][0]["case_id"], "case-a")
        self.assertEqual(report["case_statuses"][0]["structural_status"], "passed")

    def test_generated_output_gate_returns_structural_validation_failure(self) -> None:
        def fake_generate(argv):
            return 0

        def fake_openability(manifest_path):
            return {"case_count": 4, "passed_count": 4, "failed_count": 0, "results": []}

        def fake_validate(argv):
            print("Summary: cases=4 passed=3 expected_failed=0 unexpected_failed=1 skipped=0 structural_failed_checks=1")
            return 1

        output = StringIO()
        with (
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.generate_manifest_main",
                fake_generate,
            ),
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_generated_openability",
                fake_openability,
            ),
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_structure_main",
                fake_validate,
            ),
            redirect_stdout(output),
        ):
            exit_code = run_generated_output_gate([])

        self.assertEqual(exit_code, 1)
        self.assertIn("Structural validation: failed", output.getvalue())

    def test_generated_output_gate_returns_openability_failure_before_structural_validation(self) -> None:
        calls = []

        def fake_generate(argv):
            calls.append("generate")
            return 0

        def fake_openability(manifest_path):
            calls.append("openability")
            return {"case_count": 4, "passed_count": 3, "failed_count": 1, "results": []}

        def fake_validate(argv):
            calls.append("validate")
            return 0

        output = StringIO()
        with (
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.generate_manifest_main",
                fake_generate,
            ),
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_generated_openability",
                fake_openability,
            ),
            patch(
                "scripts.workflow.run_modern_docx_omml_generated_output_gate.validate_structure_main",
                fake_validate,
            ),
            redirect_stdout(output),
        ):
            exit_code = run_generated_output_gate([])

        self.assertEqual(exit_code, 1)
        self.assertEqual(calls, ["generate", "openability"])
        rendered = output.getvalue()
        self.assertIn("Openability: cases=4 passed=3 failed=1", rendered)
        self.assertIn("Openability validation: failed", rendered)


if __name__ == "__main__":
    unittest.main()
