# CP-001 - Parser question boundary stabilization

## Metadata

- Candidate ID: `CP-001`
- Status: `open`
- First observed: `2026-04-08`
- Last updated: `2026-04-08`
- Owner: `parser/contracts`
- Proposed layer: `core`

## Problem Summary

HTML -> JSON parsing still produces repeated duplicate question numbers, unknown question types, and low-confidence segments across multiple subjects.
This is a parser-layer behavior, not subject semantics.

## Cross-subject Evidence

Source: `out/phase-b-regression-20260408/samples/*/contracts/parser_report.json`

- `duplicate_question_number`: total `1885`
  - chemistry: `1063`
  - math: `599`
  - physics: `223`
- `unknown_question_type`: total `688`
  - chemistry: `313`
  - math: `262`
  - physics: `113`
- `low_parse_confidence`: total `779`
  - chemistry: `380`
  - math: `281`
  - physics: `118`

## Scope Decision (Core vs Subject)

This belongs to core parser because warning patterns are shared across Chemistry, Physics, and Math and come from header/splitting heuristics.

## Proposed Fix Class

- `parser`

## Acceptance Checks

- Keep existing contract schema stable (`output_contract.v1`, `parser_report.v1`).
- Reduce duplicate and unknown type warnings on Phase B regression set.
- Keep deterministic ordering in generated contract artifacts.

## Override Relationship

- Temporary override allowed: `no`
- Rationale: parser boundary quality must be solved in core; per-exam override would create high maintenance debt.

## Decision

- Keep as active core candidate for next parser iteration.
