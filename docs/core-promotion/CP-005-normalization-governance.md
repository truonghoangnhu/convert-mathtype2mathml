# CP-005 - Cross-subject normalization governance

## Metadata

- Candidate ID: `CP-005`
- Status: `open`
- First observed: `2026-04-08`
- Last updated: `2026-04-08`
- Owner: `core normalize + subject profiles`
- Proposed layer: `mixed`

## Problem Summary

Normalization fixes are applied in all major subjects, but rule ownership is not always explicit.
A governance split is needed to prevent domain-specific rewrites from leaking into core.

## Cross-subject Evidence

Source: `out/phase-b-regression-20260408/samples/*/qa/*.qa.json` (`totals`)

- `normalized_text_fixes_applied`: total `254`
  - chemistry: `194`
  - math: `21`
  - physics: `39`

## Scope Decision (Core vs Subject)

- Keep only strictly safe normalization in core (encoding/whitespace/entity/unit-spacing primitives).
- Keep chemistry/physics/math domain semantics in subject profiles.
- Track promotions explicitly when a rule appears in multiple subjects and remains semantically safe.

## Proposed Fix Class

- `subject-normalization`
- `cleanup`

## Acceptance Checks

- No cross-subject semantic regressions.
- Deterministic normalization diffs in regression runs.
- Explicit rule ownership documented for new normalization patches.

## Override Relationship

- Temporary override allowed: `yes`, for isolated text corruption strings only.
- Trigger to promote core/spec fix: recurring same patch pattern in multiple exams.

## Decision

- Keep as active mixed candidate with explicit core/subject ownership policy.
