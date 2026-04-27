# Modern DOCX + OMML Release Readiness (Current Scope)

Date: 2026-04-25
Decision target: practical supported/releasable path for current modern-only scope

## Readiness Matrix

| Area | Status | Evidence |
|---|---|---|
| Guardrails (modern-only, no legacy reopen) | ready | `regression_set/modern_docx_omml_operational_baseline.md` |
| Practical acceptance baseline | ready | `regression_set/modern_docx_omml_inventory.json` active cases + smoke gate |
| Operational baseline clarity | ready | `regression_set/modern_docx_omml_operational_baseline.md` |
| Runtime confidence | ready | `regression_set/modern_docx_omml_runtime_confidence_report.json` (`adequate_for_current_practical_modern_baseline=true`) |
| Local-only promotion governance | ready | `regression_set/modern_docx_omml_promotion_preflight_report.json` |
| Mixed object+OMML repo-tracked coverage | limited | `regression_set/modern_docx_omml_mixed_candidate_expansion_report.json` (`repo_tracked_mixed_candidates=0`) |

## Required vs Optional Scope

Required CI/stable baseline path (must stay green):

- `mvn -q -Dtest=DocxMathPatchWorkflowTest,DocxToHtmlCliPatchSummaryJsonlTest test`
- `python3 scripts/workflow/run_modern_docx_omml_smoke.py`
- `python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py`

Optional/local-only confidence expansion path (not required CI baseline):

- local-only mixed/object-path confidence cases in `regression_set/modern_docx_omml_inventory.json`
- promotion preflight and mixed-candidate scan reports

## Remaining Thin Spot

- No repo-tracked mixed embedded-object + native OMML candidate in required CI/stable baseline path.
- This is currently a known limitation, not a blocker for current practical modern release scope.

## Reopen Conditions

Reopen release-readiness status if any occur:

- smoke gate or generated-output gate turns red
- runtime confidence flips to not adequate
- supported modern baseline changes materially
- a legally/operationally safe mixed object+OMML candidate becomes repo-trackable and promotion-ready

## Judgment

Ready with explicit local-only limitation:

- The current modern DOCX + OMML baseline is release-ready for current practical scope.
- Mixed object+OMML remains local-only confidence evidence until a repo-trackable candidate passes promotion preflight.
