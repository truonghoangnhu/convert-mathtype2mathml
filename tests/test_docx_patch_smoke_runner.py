from __future__ import annotations

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "workflow" / "run_docx_patch_smoke.py"
SPEC = importlib.util.spec_from_file_location("run_docx_patch_smoke", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class DocxPatchSmokeRunnerTest(unittest.TestCase):
    def test_parse_patch_output_extracts_summary_and_breakdown(self) -> None:
        stdout = "\n".join(
            [
                "Patch summary: scanned=10 block=2 inline=7 native=1 unresolved=0 skipped_unsafe_inline=0 skipped_multi=0 skipped_unknown=0 multi_patched=1 multi_skipped_unsafe=0 multi_skipped_ambiguous=0",
                "Skip breakdown:",
                "- NATIVE_OMML_PRESENT=1",
                "- DRAWING_IN_RUN=0",
                "- LAST_RENDERED_PAGE_BREAK_IN_RUN=0",
            ]
        )

        parsed = MODULE.parse_patch_output(stdout)

        self.assertEqual(parsed["summary"]["scanned"], 10)
        self.assertEqual(parsed["summary"]["inline"], 7)
        self.assertEqual(parsed["breakdown"]["NATIVE_OMML_PRESENT"], 1)
        self.assertEqual(parsed["breakdown"]["DRAWING_IN_RUN"], 0)

    def test_load_registry_and_select_all_math_presets(self) -> None:
        registry = MODULE.load_preset_registry(MODULE.DEFAULT_PRESET_CONFIG)

        selected = MODULE.select_preset_names(
            registry,
            explicit_names=[],
            use_all_presets=True,
            subject_filters=["math"],
        )

        self.assertEqual(
            selected,
            [
                "math-1202",
                "math-phi",
                "math-deso-11-tb",
                "math-deso-12-small",
                "math-deso-22-small",
            ],
        )

    def test_aggregate_results_ignores_native_only_for_no_action(self) -> None:
        results = [
            {
                "preset": "chemistry-a",
                "subject": "chemistry",
                "status": "ok",
                "summary": {"scanned": 10, "inline": 8},
                "breakdown": {"NATIVE_OMML_PRESENT": 2, "DRAWING_IN_RUN": 0},
                "semantics": {"equation_scanned": 10, "equation_patched": 8, "equation_native": 2, "equation_handled": 10},
                "diagnostic_root_causes": {},
                "output": "out/a.docx",
            },
            {
                "preset": "chemistry-b",
                "subject": "chemistry",
                "status": "ok",
                "summary": {"scanned": 12, "inline": 9},
                "breakdown": {"NATIVE_OMML_PRESENT": 1, "DRAWING_IN_RUN": 0},
                "semantics": {"equation_scanned": 12, "equation_patched": 9, "equation_native": 1, "equation_handled": 10},
                "diagnostic_root_causes": {},
                "output": "out/b.docx",
            },
        ]

        aggregate = MODULE.aggregate_results(results)

        self.assertEqual(aggregate["reason_totals"]["NATIVE_OMML_PRESENT"], 3)
        self.assertEqual(aggregate["presets_with_residual_skips"], 0)
        self.assertEqual(aggregate["decision_hint"]["level"], "NO_ACTION")
        self.assertEqual(aggregate["decision_hint"]["focus"], "NONE")
        self.assertEqual(aggregate["top_residual_reasons"], [])

    def test_aggregate_results_marks_consider_patch_when_reason_repeats(self) -> None:
        results = [
            {
                "preset": "physics-a",
                "subject": "physics",
                "status": "ok",
                "summary": {"scanned": 20, "inline": 14},
                "breakdown": {"DRAWING_IN_RUN": 2, "LAST_RENDERED_PAGE_BREAK_IN_RUN": 0},
                "semantics": {"equation_scanned": 20, "equation_patched": 14, "equation_structural_residual_skips": 2},
                "diagnostic_root_causes": {},
                "output": "out/a.docx",
            },
            {
                "preset": "physics-b",
                "subject": "physics",
                "status": "ok",
                "summary": {"scanned": 22, "inline": 15},
                "breakdown": {"DRAWING_IN_RUN": 1, "LAST_RENDERED_PAGE_BREAK_IN_RUN": 0},
                "semantics": {"equation_scanned": 22, "equation_patched": 15, "equation_structural_residual_skips": 1},
                "diagnostic_root_causes": {},
                "output": "out/b.docx",
            },
        ]

        aggregate = MODULE.aggregate_results(results)

        self.assertEqual(aggregate["presets_with_residual_skips"], 2)
        self.assertEqual(aggregate["decision_hint"]["level"], "CONSIDER_PATCH")
        self.assertEqual(aggregate["decision_hint"]["focus"], "PATCH_ENGINE_STRUCTURAL")
        self.assertEqual(aggregate["top_residual_reasons"][0]["reason"], "DRAWING_IN_RUN")
        self.assertEqual(aggregate["top_residual_reasons"][0]["count"], 3)
        self.assertEqual(aggregate["top_residual_reasons"][0]["presets_affected"], 2)

    def test_aggregate_results_points_equation_residuals_to_upstream(self) -> None:
        results = [
            {
                "preset": "chem-a",
                "subject": "chemistry",
                "status": "ok",
                "summary": {"scanned": 40, "inline": 35, "unresolved": 2},
                "breakdown": {"UNRESOLVED_MANIFEST": 2},
                "semantics": {
                    "equation_scanned": 40,
                    "equation_patched": 35,
                    "equation_native": 3,
                    "equation_handled": 38,
                    "equation_structural_residual_skips": 0,
                    "unresolved_equation_upstream": 2,
                    "suppressed_non_equation_objects": 0,
                },
                "diagnostic_root_causes": {"EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST": 2},
                "output": "out/chem-a.docx",
            },
            {
                "preset": "math-a",
                "subject": "math",
                "status": "ok",
                "summary": {"scanned": 50, "inline": 48, "unresolved": 0},
                "breakdown": {"UNRESOLVED_MANIFEST": 0},
                "semantics": {
                    "equation_scanned": 50,
                    "equation_patched": 48,
                    "equation_native": 2,
                    "equation_handled": 50,
                    "equation_structural_residual_skips": 0,
                },
                "diagnostic_root_causes": {},
                "output": "out/math-a.docx",
            },
        ]

        aggregate = MODULE.aggregate_results(results)

        self.assertEqual(aggregate["top_residual_reasons"][0]["reason"], "UNRESOLVED_MANIFEST")
        self.assertEqual(aggregate["top_residual_reasons"][0]["count"], 2)
        self.assertEqual(aggregate["decision_hint"]["level"], "INVESTIGATE")
        self.assertEqual(aggregate["decision_hint"]["focus"], "EQUATION_UPSTREAM")
        self.assertEqual(
            aggregate["decision_hint"]["reason"],
            "no equation structural skips remain; residual equation cases come from upstream sidecar generation",
        )
        self.assertEqual(
            aggregate["top_diagnostic_root_causes"][0]["root_cause"],
            "EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST",
        )

    def test_aggregate_results_keeps_non_equation_residuals_out_of_patch_hint(self) -> None:
        results = [
            {
                "preset": "chem-a",
                "subject": "chemistry",
                "status": "ok",
                "summary": {"scanned": 105, "inline": 84, "block": 19, "unresolved": 2},
                "breakdown": {"UNRESOLVED_MANIFEST": 2},
                "semantics": {
                    "equation_scanned": 103,
                    "equation_patched": 103,
                    "equation_native": 0,
                    "equation_handled": 103,
                    "equation_structural_residual_skips": 0,
                    "non_equation_embedded_objects": 2,
                    "suppressed_non_equation_objects": 2,
                    "unresolved_equation_upstream": 0,
                },
                "diagnostic_root_causes": {"NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST": 2},
                "output": "out/chem-a.docx",
            }
        ]

        aggregate = MODULE.aggregate_results(results)

        self.assertEqual(aggregate["decision_hint"]["level"], "NO_ACTION")
        self.assertEqual(aggregate["decision_hint"]["focus"], "NON_EQUATION_DIAGNOSTICS")
        self.assertEqual(
            aggregate["decision_hint"]["reason"],
            "no equation residuals remain; only suppressed non-equation embedded objects remain in diagnostics",
        )
        self.assertEqual(aggregate["semantic_totals"]["non_equation_embedded_objects"], 2)
        self.assertEqual(aggregate["semantic_totals"]["suppressed_non_equation_objects"], 2)

    def test_emit_tsv_includes_aggregate_sections(self) -> None:
        results = [
            {
                "preset": "math-a",
                "subject": "math",
                "status": "ok",
                "summary": {"scanned": 5, "inline": 5},
                "breakdown": {"DRAWING_IN_RUN": 0},
                "semantics": {"equation_scanned": 5, "equation_patched": 5, "equation_handled": 5},
                "diagnostic_root_causes": {},
                "output": "out/math-a.docx",
            }
        ]
        aggregate = MODULE.aggregate_results(results)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            MODULE.emit_tsv(results, aggregate)
        output = stream.getvalue()

        self.assertIn("# preset_results", output)
        self.assertIn("# preset_semantics", output)
        self.assertIn("# aggregate_summary", output)
        self.assertIn("# aggregate_semantics", output)
        self.assertIn("# aggregate_reasons", output)
        self.assertIn("# aggregate_diagnostic_root_causes", output)
        self.assertIn("# top_residual_reasons", output)
        self.assertIn("# top_diagnostic_root_causes", output)
        self.assertIn("# decision_hint", output)
        self.assertIn("focus", output)
        self.assertIn("NO_ACTION", output)


if __name__ == "__main__":
    unittest.main()
