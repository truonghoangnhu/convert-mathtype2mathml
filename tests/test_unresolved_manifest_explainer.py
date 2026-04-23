from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "explain_unresolved_manifest.py"
SPEC = importlib.util.spec_from_file_location("explain_unresolved_manifest", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class UnresolvedManifestExplainerTest(unittest.TestCase):
    def test_non_equation_object_is_classified_as_corpus_data_issue(self) -> None:
        case = {
            "object_kind": "chemical-diagram",
            "ole_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "preview_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "bin_sidecar_exists": False,
            "bin_sidecar_usable": False,
            "bin_needed": False,
        }

        root_cause = MODULE.classify_root_cause(case)

        self.assertEqual(root_cause, "NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST")
        self.assertEqual(MODULE.decision_for_root_cause(root_cause), "CORPUS_DATA_ISSUE")

    def test_empty_bin_sidecar_is_classified_as_transpect_issue(self) -> None:
        case = {
            "object_kind": "equation",
            "ole_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "preview_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "bin_sidecar_exists": True,
            "bin_sidecar_usable": False,
            "bin_sidecar_status": "empty_math",
            "preview_sidecar_status": "missing",
            "bin_needed": True,
        }

        root_cause = MODULE.classify_root_cause(case)

        self.assertEqual(root_cause, "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST")
        self.assertEqual(MODULE.decision_for_root_cause(root_cause), "INVESTIGATE_TRANSPECT_OUTPUT")

    def test_usable_bin_sidecar_missing_from_manifest_stays_transpect_side(self) -> None:
        case = {
            "object_kind": "equation",
            "ole_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "preview_manifest": {"exact_manifest_hit": False, "resolved": False, "ambiguous_leaf": False},
            "bin_sidecar_exists": True,
            "bin_sidecar_usable": True,
            "bin_sidecar_status": "usable",
            "preview_sidecar_status": "missing",
            "bin_needed": True,
        }

        root_cause = MODULE.classify_root_cause(case)

        self.assertEqual(root_cause, "USABLE_GENERATED_SIDECAR_MISSING_FROM_MANIFEST")
        self.assertEqual(MODULE.decision_for_root_cause(root_cause), "INVESTIGATE_TRANSPECT_OUTPUT")

    def test_decision_label_prefers_transpect_over_corpus_data(self) -> None:
        cases = [
            {"decision": "CORPUS_DATA_ISSUE"},
            {"decision": "INVESTIGATE_TRANSPECT_OUTPUT"},
        ]

        self.assertEqual(MODULE.decide_label(cases), "INVESTIGATE_TRANSPECT_OUTPUT")

    def test_diagnose_manifest_part_reports_ambiguous_leaf(self) -> None:
        manifest_index = {
            "by_part": {},
            "by_leaf": {
                "image45.wmf": [
                    {"part": "/word/media/a/image45.wmf", "sidecar_exists": True, "sidecar_usable": True, "sidecar_status": "usable"},
                    {"part": "/word/media/b/image45.wmf", "sidecar_exists": True, "sidecar_usable": True, "sidecar_status": "usable"},
                ]
            },
        }

        diag = MODULE.diagnose_manifest_part("/word/media/image45.wmf", manifest_index)

        self.assertFalse(diag["resolved"])
        self.assertTrue(diag["ambiguous_leaf"])
        self.assertEqual(diag["leaf_match_count"], 2)

    def test_mathml_status_detects_empty_math(self) -> None:
        tmp_path = REPO_ROOT / "out" / "test-empty.mathml"
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text('<math xmlns="http://www.w3.org/1998/Math/MathML"/>', encoding="utf-8")
        try:
            self.assertEqual(MODULE.mathml_status(tmp_path), "empty_math")
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
