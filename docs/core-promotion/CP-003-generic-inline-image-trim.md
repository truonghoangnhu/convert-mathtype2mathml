# CP-003 - Generic inline image trim/crop governance

## Metadata

- Candidate ID: `CP-003`
- Status: `open`
- First observed: `2026-04-08`
- Last updated: `2026-04-08`
- Owner: `core image pipeline`
- Proposed layer: `core`

## Problem Summary

Inline image trimming and crop safety are active in all subjects. This logic should remain and evolve in core because behavior is not subject semantic.

## Cross-subject Evidence

Source: `out/phase-b-regression-20260408/samples/*/qa/*.qa.json` (`totals`)

- `generic_inline_image_count`: total `416`
  - chemistry: `144`
  - math: `201`
  - physics: `71`
- `generic_inline_image_trim_applied_count`: total `306`
  - chemistry: `124`
  - math: `124`
  - physics: `58`

## Scope Decision (Core vs Subject)

Trim candidate detection and crop safeguards are generic rendering concerns and should be centralized in core images/cleanup logic.

## Proposed Fix Class

- `render`
- `cleanup`
- `qa-gate`

## Acceptance Checks

- Preserve image readability and context.
- Avoid regressions in bad-crop or blank-image metrics.
- Keep deterministic image handling across regression set.

## Override Relationship

- Temporary override allowed: `yes`, for singular asset keep/suppress decisions.
- Trigger to promote core fix: recurring pattern in 2+ subjects.

## Decision

- Keep as active core candidate.
