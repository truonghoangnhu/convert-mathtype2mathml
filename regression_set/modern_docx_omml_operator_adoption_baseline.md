# Modern DOCX + OMML Operator Adoption Baseline

Date: 2026-04-25
Audience: maintainers/operators handling modern-path CI failures and candidate intake

## 1. Supported vs Local-Only vs Out-Of-Scope

Supported required CI/stable path:

- `mvn -q -Dtest=DocxMathPatchWorkflowTest,DocxToHtmlCliPatchSummaryJsonlTest test`
- `python3 scripts/workflow/run_modern_docx_omml_smoke.py`
- `python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py`
- Active repo-tracked modern fixtures in `regression_set/modern_docx_omml_inventory.json` (`status=active`).

Local-only confidence path (not release-blocking by itself):

- `status=local_only` modern cases in `regression_set/modern_docx_omml_inventory.json`
- `regression_set/modern_docx_omml_mixed_candidate_expansion_report.json`
- `regression_set/modern_docx_omml_promotion_preflight_report.json`

Out-of-scope / do-not-promote path:

- legacy `.doc` / DSMT4 reopening work
- fixture additions that require behavior-default changes, workflow/schema redesign, or unclear provenance

## 2. PR/Check Failure Triage Flow (Operator)

1. Check `python3 scripts/workflow/run_modern_docx_omml_smoke.py`.
- If `unexpected_failed>0`: treat as supported-baseline regression first.
- If only `expected_failed` negative case appears: not a new regression by itself.

2. Check `python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py`.
- If openability or structural validation fails: treat as release-blocking modern-path issue.
- Inspect artifact first: `out/modern-docx-omml-generated/modern_docx_omml_generated_output_gate_report.json`.

3. Interpret patch-path diagnostics in the gate output/artifact.
- `drift_class=serializer_only_drift`: normalization-only serializer difference; usually non-blocking unless policy changes.
- `drift_class=structural_drift`: structure/count/placement drift; treat as blocking until explained/fixed.
- `omml_attention` fields (`omml_preservation`, `omml_drift_class`, `omml_drift_warning`): focus list for fast case-by-case triage.

4. Distinguish local-only candidate issue.
- If issue exists only in `local_only` candidate runs/reports and required CI/stable path remains green, keep it out of release-blocking lane.

## 3. Local-Only Candidate Handoff Rules

When a local-only candidate looks promising:

- Keep local-only when provenance/repo-trackability is unresolved, or CI-safe scope is unclear.
- Run promotion preflight (`python3 scripts/workflow/run_modern_docx_omml_promotion_preflight.py`) before any promotion request.
- Justify repo-tracked promotion only when candidate is simultaneously:
  - structurally suitable
  - CI-safe
  - repo-trackable
  - meaningful confidence gain over active supported fixtures

If any preflight blocker remains, do not promote; keep candidate local-only and record in preflight report.
