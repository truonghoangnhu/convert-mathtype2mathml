from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.workflow.generate_modern_docx_omml_output_manifest import DEFAULT_CASE_IDS, build_manifest_case
from scripts.workflow.render_modern_docx_omml_gate_summary import (
    main as render_gate_summary_main,
    render_summary_markdown,
)
from scripts.workflow.run_modern_docx_omml_generated_output_gate import (
    _build_patch_path_diagnostics,
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


def _write_serializer_normalized_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default ContentType="application/vnd.openxmlformats-package.relationships+xml" Extension="rels"/>'
            '<Default ContentType="application/xml" Extension="xml"/>'
            '<Override ContentType="application/vnd.openxmlformats-package.core-properties+xml" PartName="/docProps/core.xml"/>'
            '<Override ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml" PartName="/word/document.xml"/>'
            "</Types>",
        )
        docx.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="word/document.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
            '<Relationship Id="rId2" Target="docProps/core.xml" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"/>'
            "</Relationships>",
        )
        docx.writestr("word/document.xml", document_xml)
        docx.writestr(
            "docProps/core.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>',
        )


def _write_modern_source_docx(path: Path, document_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '  <Default Extension="xml" ContentType="application/xml"/>\n'
            '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
            "</Types>\n",
        )
        docx.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
            "</Relationships>\n",
        )
        docx.writestr("word/document.xml", document_xml)


class ModernDocxOmmlValidatorTests(unittest.TestCase):
    def test_structural_checks_cover_supported_acceptance_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "sample.docx"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Inline equation: </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> remains in text flow.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
""",
            )
            inspection = inspect_docx(docx_path)
            checks = build_structural_checks({"expected": {}}, inspection)

            check_names = {check["name"] for check in checks}
            self.assertTrue(
                {
                    "document_xml_exists",
                    "document_xml_parseable",
                    "equation_count",
                    "block_equation_count",
                    "inline_equation_count",
                    "appears_inline_math",
                    "appears_block_math",
                    "basic_omml_structure_present",
                    "placement_summary",
                    "inline_paragraph_run_context_safe",
                    "block_omathpara_context_safe",
                    "surrounding_non_math_text_preserved",
                    "paragraph_run_safety_summary",
                }.issubset(check_names)
            )

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
            self.assertTrue(result["inline_paragraph_run_context_safe"])
            self.assertTrue(result["block_omathpara_context_safe"])
            self.assertFalse(result["surrounding_non_math_text_preserved"])
            self.assertEqual(
                result["paragraph_run_safety_summary"],
                "inline_paragraphs=1 inline_with_text=0 inline_with_text_before_after=0 block_paragraphs=1 multi_inline_paragraphs=0",
            )
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
            self.assertEqual(by_name["equation_count"]["actual"], 1)
            self.assertEqual(by_name["equation_count"]["expected"], 1)
            self.assertIsNone(by_name["basic_omml_structure_present"]["expected"])
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

    def test_patch_path_diagnostics_compare_source_and_generated_output_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_docx_path = tmp_path / "source.docx"
            output_docx_path = tmp_path / "generated.docx"
            manifest_path = tmp_path / "manifest.json"
            _write_docx(
                source_docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Solve </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> and </w:t></w:r>
      <m:oMath><m:r><m:t>y</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> in the same paragraph.</w:t></w:r>
    </w:p>
  </w:body>
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
            manifest_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "generated-inline",
                                "source_docx": str(source_docx_path),
                                "generated_docx": str(output_docx_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            diagnostics = _build_patch_path_diagnostics(manifest_path)

            self.assertEqual(diagnostics["case_count"], 1)
            self.assertEqual(diagnostics["drift_candidate_count"], 1)
            case = diagnostics["cases"][0]
            self.assertEqual(case["case_id"], "generated-inline")
            self.assertEqual(case["source"]["equation_count"], 2)
            self.assertEqual(case["output"]["equation_count"], 1)
            self.assertIn("inline OMML only", case["output"]["placement_summary"])
            self.assertEqual(
                case["drift_origin_hint"],
                "equation_count_or_block_inline_split_changed_across_patch_docx",
            )
            self.assertEqual(case["drift_class"], "structural_drift")

    def test_patch_path_diagnostics_classifies_serializer_only_drift_for_native_omml_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_docx_path = tmp_path / "source.docx"
            output_docx_path = tmp_path / "generated.docx"
            manifest_path = tmp_path / "manifest.json"
            source_document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Solve </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> and </w:t></w:r>
      <m:oMath><m:r><m:t>y</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> in the same paragraph.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
            output_document_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Solve </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> and </w:t></w:r>
      <m:oMath><m:r><m:t>y</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> in the same paragraph.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
            _write_modern_source_docx(source_docx_path, source_document_xml)
            _write_serializer_normalized_docx(output_docx_path, output_document_xml)
            manifest_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "native-serializer-only",
                                "source_docx": str(source_docx_path),
                                "generated_docx": str(output_docx_path),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            diagnostics = _build_patch_path_diagnostics(manifest_path)

            self.assertEqual(diagnostics["case_count"], 1)
            self.assertEqual(diagnostics["drift_candidate_count"], 0)
            self.assertEqual(diagnostics["drift_class_counts"]["serializer_only_drift"], 1)
            case = diagnostics["cases"][0]
            self.assertEqual(case["drift_origin_hint"], "no_structural_drift_detected")
            self.assertEqual(case["drift_class"], "serializer_only_drift")
            self.assertEqual(case["drift_class_reason"], "package_xml_normalization_only")
            self.assertEqual(case["package_diff_details"]["extra_output_parts"], ["docProps/core.xml"])
            self.assertIn("word/document.xml", case["package_diff_details"]["differing_parts"])

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
        self.assertTrue(expected["basic_omml_structure_present"])
        self.assertEqual(expected["computed_placement_summary"], "inline OMML only: inline_oMath=1")
        self.assertTrue(expected["valid_omath_omathpara_structure"])
        self.assertTrue(expected["inline_paragraph_run_context_safe"])
        self.assertTrue(expected["block_omathpara_context_safe"])
        self.assertTrue(expected["surrounding_non_math_text_preserved"])
        self.assertEqual(
            expected["paragraph_run_safety_summary"],
            "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=0",
        )

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
        self.assertTrue(inspection["inline_paragraph_run_context_safe"])
        self.assertTrue(inspection["block_omathpara_context_safe"])
        self.assertTrue(inspection["surrounding_non_math_text_preserved"])
        self.assertEqual(
            inspection["paragraph_run_safety_summary"],
            "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=1 multi_inline_paragraphs=0",
        )

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
        self.assertTrue(inspection["inline_paragraph_run_context_safe"])
        self.assertTrue(inspection["block_omathpara_context_safe"])
        self.assertTrue(inspection["surrounding_non_math_text_preserved"])
        self.assertEqual(
            inspection["paragraph_run_safety_summary"],
            "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=0",
        )

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
        self.assertIn("paragraph_run_safety:", rendered)
        self.assertIn("structural_diff: all expected structural checks matched", rendered)
        self.assertNotIn("check equation_count: fail", rendered)

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
            self.assertIn("actual='inline OMML only: inline_oMath=1'", rendered)
            self.assertIn("expected='block OMML only: oMathPara=1'", rendered)

    def test_structural_entrypoint_fails_on_equation_count_drift(self) -> None:
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
                                "case_id": "inline-count-drift",
                                "source_docx": "inline.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 2,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 1,
                                    "appears_inline_math": True,
                                    "appears_block_math": False,
                                    "basic_omml_structure_present": True,
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
            output = StringIO()

            with redirect_stdout(output):
                exit_code = validate_modern_docx_omml_structure(["--inventory", str(inventory_path)])

            rendered = output.getvalue()
            self.assertEqual(case["result"], "unexpected_failed")
            self.assertEqual(case["status"], "failed")
            self.assertEqual(exit_code, 1)
            self.assertEqual(report["unexpected_failed_count"], 1)
            self.assertIn("structural_failed_checks=1", rendered)
            self.assertIn("check equation_count: fail", rendered)
            self.assertIn("actual=1", rendered)
            self.assertIn("expected=2", rendered)

    def test_structural_entrypoint_fails_on_paragraph_run_safety_expectation_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docx_path = tmp_path / "inline.docx"
            inventory_path = tmp_path / "inventory.json"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Inline equation: </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> remains in text flow.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
""",
            )
            inventory_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "inline-safety-drift",
                                "source_docx": "inline.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 1,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 1,
                                    "appears_inline_math": True,
                                    "appears_block_math": False,
                                    "basic_omml_structure_present": True,
                                    "valid_omath_omathpara_structure": True,
                                    "surrounding_non_math_text_preserved": False,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = validate_inventory(inventory_path)
            case = report["cases"][0]
            output = StringIO()

            with redirect_stdout(output):
                exit_code = validate_modern_docx_omml_structure(["--inventory", str(inventory_path)])

            rendered = output.getvalue()
            self.assertEqual(case["result"], "unexpected_failed")
            self.assertEqual(case["status"], "failed")
            self.assertEqual(exit_code, 1)
            self.assertEqual(report["unexpected_failed_count"], 1)
            self.assertIn("structural_failed_checks=1", rendered)
            self.assertIn("check surrounding_non_math_text_preserved: fail", rendered)
            self.assertIn("actual=True", rendered)
            self.assertIn("expected=False", rendered)

    def test_structural_entrypoint_fails_on_paragraph_run_safety_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docx_path = tmp_path / "multi-inline.docx"
            inventory_path = tmp_path / "inventory.json"
            _write_docx(
                docx_path,
                f"""<w:document xmlns:w="{WORD_NS}" xmlns:m="{OMML_NS}">
  <w:body>
    <w:p>
      <w:r><w:t xml:space="preserve">Solve </w:t></w:r>
      <m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> and </w:t></w:r>
      <m:oMath><m:r><m:t>y</m:t></m:r></m:oMath>
      <w:r><w:t xml:space="preserve"> in the same paragraph.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
""",
            )
            inventory_path.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "case_id": "multi-inline-safety-summary-drift",
                                "source_docx": "multi-inline.docx",
                                "classification": "supported",
                                "expected": {
                                    "equation_count": 2,
                                    "block_equation_count": 0,
                                    "inline_equation_count": 2,
                                    "appears_inline_math": True,
                                    "appears_block_math": False,
                                    "basic_omml_structure_present": True,
                                    "valid_omath_omathpara_structure": True,
                                    "paragraph_run_safety_summary": "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=0 block_paragraphs=0 multi_inline_paragraphs=1",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            report = validate_inventory(inventory_path)
            case = report["cases"][0]
            output = StringIO()

            with redirect_stdout(output):
                exit_code = validate_modern_docx_omml_structure(["--inventory", str(inventory_path)])

            rendered = output.getvalue()
            self.assertEqual(case["result"], "unexpected_failed")
            self.assertEqual(case["status"], "failed")
            self.assertEqual(exit_code, 1)
            self.assertEqual(report["unexpected_failed_count"], 1)
            self.assertIn("structural_failed_checks=1", rendered)
            self.assertIn("check paragraph_run_safety_summary: fail", rendered)
            self.assertIn(
                "actual='inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=1'",
                rendered,
            )
            self.assertIn(
                "expected='inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=0 block_paragraphs=0 multi_inline_paragraphs=1'",
                rendered,
            )

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
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate._build_patch_path_diagnostics",
                    lambda _: {
                        "case_count": 4,
                        "drift_candidate_count": 0,
                        "drift_class_counts": {
                            "no_drift": 2,
                            "serializer_only_drift": 0,
                            "structural_drift": 0,
                        },
                        "cases": [
                            {
                                "case_id": "case-a",
                                "drift_origin_hint": "no_structural_drift_detected",
                                "drift_class": "no_drift",
                            },
                            {
                                "case_id": "case-b",
                                "drift_origin_hint": "no_structural_drift_detected",
                                "drift_class": "no_drift",
                            },
                        ],
                    },
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
                            {
                                "case_id": "case-a",
                                "result": "passed",
                                "structural_checks": [
                                    {"name": "equation_count", "expected": 1, "actual": 1, "passed": True},
                                    {"name": "placement_summary", "expected": "inline OMML only: inline_oMath=1", "actual": "inline OMML only: inline_oMath=1", "passed": True},
                                ],
                            },
                            {
                                "case_id": "case-b",
                                "result": "passed",
                                "structural_checks": [
                                    {"name": "equation_count", "expected": 2, "actual": 2, "passed": True},
                                ],
                            },
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
        self.assertIn("Structural drift summary: no failed structural diffs", rendered)
        self.assertIn("Patch-path diagnostics: cases=4 drift_candidates=0 serializer_only=0", rendered)
        self.assertEqual(report["manifest_path"], str(manifest_path))
        self.assertEqual(report["generation_result"], "passed")
        self.assertEqual(report["openability_summary"]["status"], "passed")
        self.assertEqual(report["structural_summary"]["status"], "passed")
        self.assertEqual(report["overall_gate_result"], "passed")
        self.assertEqual(report["case_statuses"][0]["case_id"], "case-a")
        self.assertEqual(report["case_statuses"][0]["structural_status"], "passed")
        self.assertEqual(report["structural_diffs"][0]["case_id"], "case-a")
        self.assertEqual(report["structural_diffs"][0]["status"], "passed")
        self.assertEqual(report["structural_diffs"][0]["structural_checks"][0]["name"], "equation_count")
        self.assertTrue(report["structural_diffs"][0]["structural_checks"][0]["passed"])
        self.assertEqual(report["patch_path_diagnostics"]["case_count"], 4)
        self.assertEqual(report["patch_path_diagnostics"]["drift_candidate_count"], 0)
        self.assertEqual(report["patch_path_diagnostics"]["drift_class_counts"]["no_drift"], 2)

    def test_generated_output_gate_returns_structural_validation_failure(self) -> None:
        def fake_generate(argv):
            return 0

        def fake_openability(manifest_path):
            return {"case_count": 4, "passed_count": 4, "failed_count": 0, "results": []}

        def fake_validate(argv):
            print("Summary: cases=4 passed=3 expected_failed=0 unexpected_failed=1 skipped=0 structural_failed_checks=1")
            return 1

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
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate._build_patch_path_diagnostics",
                    lambda _: {
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
                                "source": {"equation_count": 2, "placement_summary": "mixed", "paragraph_run_safety_summary": "source-safe"},
                                "output": {"equation_count": 1, "placement_summary": "inline", "paragraph_run_safety_summary": "output-safe"},
                                "drift_origin_hint": "equation_count_or_block_inline_split_changed_across_patch_docx",
                                "drift_class": "structural_drift",
                            }
                        ],
                    },
                ),
                patch(
                    "scripts.workflow.run_modern_docx_omml_generated_output_gate._build_structural_report",
                    lambda _: {
                        "case_count": 4,
                        "passed_count": 3,
                        "expected_failed_count": 0,
                        "unexpected_failed_count": 1,
                        "skipped_count": 0,
                        "structural_failed_check_count": 1,
                        "cases": [
                            {
                                "case_id": "case-a",
                                "result": "unexpected_failed",
                                "structural_checks": [
                                    {"name": "equation_count", "expected": 2, "actual": 1, "passed": False},
                                    {"name": "placement_summary", "expected": "mixed inline/block OMML: inline_oMath=1 oMathPara=1", "actual": "inline OMML only: inline_oMath=1", "passed": False},
                                ],
                            }
                        ],
                    },
                ),
                redirect_stdout(output),
            ):
                exit_code = run_generated_output_gate([])

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("Structural validation: failed", rendered)
        self.assertIn("Structural drift summary:", rendered)
        self.assertIn("- case-a", rendered)
        self.assertIn("equation_count: expected=2 actual=1", rendered)
        self.assertIn(
            "placement_summary: expected='mixed inline/block OMML: inline_oMath=1 oMathPara=1' actual='inline OMML only: inline_oMath=1'",
            rendered,
        )
        self.assertIn("Patch-path diagnostics: cases=1 drift_candidates=1", rendered)
        self.assertIn(
            "- case-a: equation_count_or_block_inline_split_changed_across_patch_docx",
            rendered,
        )
        self.assertEqual(report["overall_gate_result"], "failed")
        self.assertEqual(report["structural_diffs"][0]["case_id"], "case-a")
        self.assertFalse(report["structural_diffs"][0]["structural_checks"][0]["passed"])
        self.assertEqual(report["structural_diffs"][0]["structural_checks"][0]["expected"], 2)
        self.assertEqual(report["structural_diffs"][0]["structural_checks"][0]["actual"], 1)
        self.assertEqual(report["patch_path_diagnostics"]["drift_candidate_count"], 1)
        self.assertEqual(
            report["patch_path_diagnostics"]["cases"][0]["drift_origin_hint"],
            "equation_count_or_block_inline_split_changed_across_patch_docx",
        )

    def test_generated_output_gate_report_keeps_paragraph_run_safety_diffs(self) -> None:
        def fake_generate(argv):
            return 0

        def fake_openability(manifest_path):
            return {"case_count": 1, "passed_count": 1, "failed_count": 0, "results": []}

        def fake_validate(argv):
            print("Summary: cases=1 passed=0 expected_failed=0 unexpected_failed=1 skipped=0 structural_failed_checks=2")
            return 1

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
                        "case_count": 1,
                        "passed_count": 0,
                        "expected_failed_count": 0,
                        "unexpected_failed_count": 1,
                        "skipped_count": 0,
                        "structural_failed_check_count": 2,
                        "cases": [
                            {
                                "case_id": "case-a",
                                "result": "unexpected_failed",
                                "structural_checks": [
                                    {
                                        "name": "surrounding_non_math_text_preserved",
                                        "expected": False,
                                        "actual": True,
                                        "passed": False,
                                    },
                                    {
                                        "name": "paragraph_run_safety_summary",
                                        "expected": "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=0 block_paragraphs=0 multi_inline_paragraphs=1",
                                        "actual": "inline_paragraphs=1 inline_with_text=1 inline_with_text_before_after=1 block_paragraphs=0 multi_inline_paragraphs=1",
                                        "passed": False,
                                    },
                                ],
                            }
                        ],
                    },
                ),
                redirect_stdout(output),
            ):
                exit_code = run_generated_output_gate([])

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(report["overall_gate_result"], "failed")
        self.assertEqual(report["case_statuses"][0]["gate_status"], "failed")
        self.assertEqual(report["structural_diffs"][0]["case_id"], "case-a")
        by_name = {check["name"]: check for check in report["structural_diffs"][0]["structural_checks"]}
        self.assertFalse(by_name["surrounding_non_math_text_preserved"]["passed"])
        self.assertEqual(by_name["surrounding_non_math_text_preserved"]["expected"], False)
        self.assertEqual(by_name["surrounding_non_math_text_preserved"]["actual"], True)
        self.assertFalse(by_name["paragraph_run_safety_summary"]["passed"])
        self.assertIn("inline_with_text_before_after=0", by_name["paragraph_run_safety_summary"]["expected"])
        self.assertIn("inline_with_text_before_after=1", by_name["paragraph_run_safety_summary"]["actual"])

    def test_render_gate_summary_markdown_reports_success_line_when_no_failed_diffs(self) -> None:
        markdown = render_summary_markdown(
            {
                "overall_gate_result": "passed",
                "structural_summary": {
                    "case_count": 4,
                    "passed_count": 4,
                    "expected_failed_count": 0,
                    "unexpected_failed_count": 0,
                    "skipped_count": 0,
                    "structural_failed_check_count": 0,
                },
                "structural_diffs": [
                    {
                        "case_id": "case-a",
                        "structural_checks": [
                            {"name": "equation_count", "expected": 1, "actual": 1, "passed": True}
                        ],
                    }
                ],
            }
        )

        self.assertIn("## Modern DOCX + OMML Generated-Output Gate", markdown)
        self.assertIn("- Overall gate result: `passed`", markdown)
        self.assertIn("No failed structural diffs.", markdown)
        self.assertNotIn("### Failed Structural Diffs", markdown)

    def test_render_gate_summary_markdown_reports_failed_only_structural_diffs(self) -> None:
        markdown = render_summary_markdown(
            {
                "overall_gate_result": "failed",
                "structural_summary": {
                    "case_count": 4,
                    "passed_count": 3,
                    "expected_failed_count": 0,
                    "unexpected_failed_count": 1,
                    "skipped_count": 0,
                    "structural_failed_check_count": 2,
                },
                "structural_diffs": [
                    {
                        "case_id": "case-a",
                        "structural_checks": [
                            {"name": "equation_count", "expected": 2, "actual": 1, "passed": False},
                            {"name": "placement_summary", "expected": "mixed", "actual": "inline", "passed": False},
                            {"name": "appears_inline_math", "expected": True, "actual": True, "passed": True},
                        ],
                    }
                ],
            }
        )

        self.assertIn("### Failed Structural Diffs", markdown)
        self.assertIn("| case-a | equation_count | `2` | `1` |", markdown)
        self.assertIn("| case-a | placement_summary | `'mixed'` | `'inline'` |", markdown)
        self.assertNotIn("appears_inline_math", markdown)

    def test_render_gate_summary_cli_writes_success_markdown_to_github_step_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_path = tmp_path / "gate-report.json"
            summary_path = tmp_path / "step-summary.md"
            report_path.write_text(
                json.dumps(
                    {
                        "overall_gate_result": "passed",
                        "structural_summary": {
                            "case_count": 4,
                            "passed_count": 4,
                            "expected_failed_count": 0,
                            "unexpected_failed_count": 0,
                            "skipped_count": 0,
                            "structural_failed_check_count": 0,
                        },
                        "structural_diffs": [
                            {
                                "case_id": "case-a",
                                "structural_checks": [
                                    {"name": "equation_count", "expected": 1, "actual": 1, "passed": True}
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=False):
                exit_code = render_gate_summary_main(
                    ["--report", str(report_path), "--write-github-step-summary"]
                )

            rendered = summary_path.read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertIn("## Modern DOCX + OMML Generated-Output Gate", rendered)
            self.assertIn("No failed structural diffs.", rendered)
            self.assertNotIn("### Failed Structural Diffs", rendered)

    def test_render_gate_summary_cli_writes_failed_only_entries_to_github_step_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_path = tmp_path / "gate-report.json"
            summary_path = tmp_path / "step-summary.md"
            report_path.write_text(
                json.dumps(
                    {
                        "overall_gate_result": "failed",
                        "structural_summary": {
                            "case_count": 4,
                            "passed_count": 3,
                            "expected_failed_count": 0,
                            "unexpected_failed_count": 1,
                            "skipped_count": 0,
                            "structural_failed_check_count": 2,
                        },
                        "structural_diffs": [
                            {
                                "case_id": "case-a",
                                "structural_checks": [
                                    {"name": "equation_count", "expected": 2, "actual": 1, "passed": False},
                                    {"name": "placement_summary", "expected": "mixed", "actual": "inline", "passed": False},
                                    {"name": "appears_inline_math", "expected": True, "actual": True, "passed": True},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=False):
                exit_code = render_gate_summary_main(
                    ["--report", str(report_path), "--write-github-step-summary"]
                )

            rendered = summary_path.read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertIn("### Failed Structural Diffs", rendered)
            self.assertIn("| case-a | equation_count | `2` | `1` |", rendered)
            self.assertIn("| case-a | placement_summary | `'mixed'` | `'inline'` |", rendered)
            self.assertNotIn("appears_inline_math", rendered)

    def test_render_gate_summary_cli_requires_github_step_summary_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_path = tmp_path / "gate-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "overall_gate_result": "passed",
                        "structural_summary": {
                            "case_count": 4,
                            "passed_count": 4,
                            "expected_failed_count": 0,
                            "unexpected_failed_count": 0,
                            "skipped_count": 0,
                            "structural_failed_check_count": 0,
                        },
                        "structural_diffs": [],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(SystemExit) as exc:
                    render_gate_summary_main(
                        ["--report", str(report_path), "--write-github-step-summary"]
                    )

            self.assertEqual(str(exc.exception), "GITHUB_STEP_SUMMARY is not set")

    def test_render_gate_summary_cli_requires_existing_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_report_path = Path(tmp) / "missing-gate-report.json"

            with self.assertRaises(SystemExit) as exc:
                render_gate_summary_main(["--report", str(missing_report_path)])

            self.assertEqual(
                str(exc.exception),
                f"report not found: {missing_report_path.resolve()}",
            )

    def test_render_gate_summary_cli_reports_malformed_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "malformed-gate-report.json"
            report_path.write_text("{not-json", encoding="utf-8")

            with self.assertRaises(SystemExit) as exc:
                render_gate_summary_main(["--report", str(report_path)])

            self.assertIn(
                f"report JSON could not be parsed: {report_path.resolve()}",
                str(exc.exception),
            )

    def test_render_gate_summary_cli_tolerates_missing_top_level_keys_with_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "partial-gate-report.json"
            report_path.write_text(json.dumps({"structural_diffs": []}), encoding="utf-8")
            output = StringIO()

            with redirect_stdout(output):
                exit_code = render_gate_summary_main(["--report", str(report_path)])

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("## Modern DOCX + OMML Generated-Output Gate", rendered)
            self.assertIn("- Overall gate result: `unknown`", rendered)
            self.assertIn(
                "- Structural summary: `cases=0 passed=0 expected_failed=0 unexpected_failed=0 skipped=0 structural_failed_checks=0`",
                rendered,
            )
            self.assertIn("No failed structural diffs.", rendered)

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
