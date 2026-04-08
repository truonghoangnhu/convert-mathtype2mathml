# Answer Reconciliation Examples v1

Generated fixture outputs (contract/parser/qa examples) are under:

- `out/answer-reconcile-fixtures/`
- summary index: `out/answer-reconcile-fixtures/fixture-results.json`
- dedicated regression inventory: `regression_set/answer_pipeline_inventory.json`
- dedicated runner: `scripts/regression/run_answer_pipeline_regression.py`

Cases:

1. `case1_mc_agreement`
- local + summary agree
- expected reconciliation: `resolved`

2. `case2_tf_fill`
- true/false summary fills missing local subanswers
- expected reconciliation: `resolved_with_fill`

3. `case3_short_norm_equiv`
- local `12,5` vs summary `12.5`
- expected reconciliation: `resolved_normalized_equivalent`

4. `case4_essay_rubric`
- rubric extracted from `R.` marker
- expected answer mode: `rubric`

5. `case5_conflict_local_summary`
- local vs summary mismatch
- expected reconciliation: `conflict`

6. `case6_ambiguous_summary_zone`
- duplicate/ambiguous summary zone
- expected QA flags include `answer_summary_zone_ambiguous`

7. `case7_override_applied`
- manual `answer_override` participates as `manual_override` source
- expected reconciliation: `resolved` with preserved conflict evidence

8. `case8_no_summary_clear_local`
- no answer summary zone, local answer extraction remains clear/high-confidence
- expected `answer_summary_zone_missing` severity: `info`

Per-case artifacts:

- `exam_bundle.json`
- `question_bank_items.json`
- `parser_report.json`
- `qa.json`
- `manifest.json`
- `override_audit.json`
