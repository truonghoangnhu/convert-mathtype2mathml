# numeric_tolerance_reconciliation_plan_v1.md

## Purpose

This note defines the v1 roadmap for numeric-tolerance reconciliation in the converter/parser layer.

Status on 2026-04-08:

- design only
- no runtime implementation in this pass
- existing answer pipeline v1 stays unchanged

## Scope (planned)

Numeric tolerance will be considered for reconciliation only, not for question segmentation or math/image conversion.

Primary target:

1. short-answer numeric values (raw/normalized)

Secondary target (later, optional):

2. numeric subanswers inside true/false variants that carry calculated values before boolean mapping

Out of first implementation scope:

- single-choice letter answers
- essay rubric reconciliation
- symbolic equivalence engines (CAS-level matching)

## Proposed JSON extensions (future)

No breaking changes to current fields. Additive fields only.

1. `reconciliation.status`
- add: `resolved_with_tolerance`

2. `reconciliation` detail object (new optional keys)
- `tolerance_policy_id`
- `tolerance_type` (`absolute` | `relative` | `significant_figures`)
- `tolerance_value`
- `tolerance_evidence` (raw compared values + normalized deltas)

3. `answer_key` (short answer mode)
- keep current `accepted_answers[]`
- optionally add metadata per accepted answer:
  - `numeric_value`
  - `unit_normalized`

4. `answer_sources[].details`
- optional numeric-compare fields per source to preserve auditability

## Reconciliation behavior (future)

For short-answer reconciliation:

1. exact normalized match -> existing `resolved` / `resolved_normalized_equivalent`
2. mismatch but within configured tolerance -> `resolved_with_tolerance`
3. mismatch outside tolerance -> existing `needs_review` / `blocked`

Tolerance must never silently overwrite evidence. All compared values remain in source details and QA logs.

## QA and gate implications (future)

Planned QA issue families:

- `short_answer_tolerance_applied` (`info`)
- `short_answer_tolerance_policy_missing` (`warning`)
- `short_answer_tolerance_conflict` (`warning` or `blocker` by policy)
- `short_answer_tolerance_out_of_range` (`blocker` when canonical cannot be resolved)

Parser/importer readiness:

- tolerance-applied cases are measurable
- unresolved numeric ambiguity still contributes to blocker metrics

## Non-goals for v1

1. No tolerance implementation for this closeout pass.
2. No cross-subject policy auto-inference.
3. No migration of answer logic into question_bank/frontend.
4. No redesign of current answer summary extraction/reconciliation model.

## Implementation staging (future)

1. Add policy schema and validation (`tolerance_policy` config).
2. Add parser-side numeric compare module for short answers.
3. Emit additive reconciliation metadata + new status.
4. Extend QA matrix and parser gate thresholds with tolerance-specific metrics.
5. Add dedicated tolerance fixtures to answer regression group.
