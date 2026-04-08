# Parser Quality Gate v1

Purpose: make parser stability measurable and enforceable for importer-readiness.

## Config

- `regression_set/parser_quality_gate_v1.json`
- schema: `parser_quality_gate.v1`

## Subject-aware thresholds

Configured by subject:

- `min_avg_confidence`
- `max_unknown_question_type_ratio`
- `max_warning_per_question`
- `min_question_count`

Category overrides are supported (for example `hard_ole_preview`, `omml_clean`).

Global limits:

- `max_orphan_asset_count`
- `max_orphan_math_fragment_count`
- `max_answer_blocker_count`
- `max_canonical_answer_missing_count`
- `max_answer_conflict_count`
- `max_unresolved_reconciliation_count`

## Fail vs Review Conditions

The gate separates:

- hard failures
- review-only findings

### Hard failures

A sample fails parser gate when any enabled hard condition is violated, including:

1. question count violation
2. average confidence below threshold
3. unknown question type ratio above threshold
4. orphan asset/math counts above threshold
5. answer reconciliation blocker count above threshold
6. canonical answer missing count above threshold
7. answer conflict count above threshold
8. unresolved reconciliation count above threshold

### Review-only findings

`warning_per_question` is tracked as a review-only threshold:

- it does not fail the parser gate directly
- it is still emitted in the parser gate report
- it can raise sample status to `passed_with_review`

Note on `answer_summary_zone_missing`:

- this signal is context-tuned in answer reconciliation stage
- when local extraction is strong/complete, severity is downgraded to `info`
- parser gate does not fail on this signal directly; importer-readiness is still enforced by blocker/conflict/missing-canonical thresholds above

## Runtime wiring

Parser gate is evaluated in:

- `scripts/regression/run_phase_b_regression.py`

Per-sample output includes:

- `parser_gate.passed`
- `parser_gate.review_required`
- `parser_gate.hard_failures`
- `parser_gate.review_findings`
- `parser_gate.failures`
- measured parser metrics and active thresholds

If `--enforce-gates` is enabled (default), parser gate failures make the regression run fail.
