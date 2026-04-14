# Answer Pipeline Summary v1

This note replaces the longer answer-pipeline working docs with one shorter reference.

## Purpose

Keep answer normalization, reconciliation, and extraction logic canonical inside the parser output model.
The bank/import/export layers should consume the parsed answer model, not re-derive meaning from Word formatting.

## Core Rules

- `source cues` are allowed, but they must not become the source of truth.
- If confidence is low or the structure is ambiguous, emit an issue and mark the item for review.
- Do not let formatting-only hints drive answer semantics across multiple pipeline layers.

## Canonical answer modes

- `single_choice`
- `multiple_select`
- `boolean`
- `short_answer`
- `rubric`
- `none`

## What this summary covers

- answer normalization
- answer reconciliation
- answer summary extraction
- numeric tolerance handling for answer matching

## Replace / consolidate

- `answer_normalization_spec_v1.md`
- `answer_reconciliation_spec_v1.md`
- `answer_summary_extraction_spec_v1.md`
- `numeric_tolerance_reconciliation_plan_v1.md`

