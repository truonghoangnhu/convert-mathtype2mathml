# CP-004 - Structural HTML cleanup consistency

## Metadata

- Candidate ID: `CP-004`
- Status: `open`
- First observed: `2026-04-08`
- Last updated: `2026-04-08`
- Owner: `core html cleanup`
- Proposed layer: `core`

## Problem Summary

HTML structure cleanup work (empty paragraph removal, table boundary cleanup, malformed math-flow cleanup) is exercised heavily in all subjects and should stay centralized.

## Cross-subject Evidence

Source: `out/phase-b-regression-20260408/samples/*/qa/*.qa.json` (`totals`)

- `table_adjacent_empty_paragraph_cleanup_count`: total `221`
  - chemistry: `69`
  - math: `110`
  - physics: `42`
- `table_cell_empty_paragraph_removed_count`: total `808`
  - chemistry: `89`
  - math: `267`
  - physics: `452`
- `math_block_flow_cleanup_count`: total `21`
  - chemistry: `3`
  - math: `14`
  - physics: `4`

## Scope Decision (Core vs Subject)

These are structural cleanup behaviors independent of subject domain semantics.

## Proposed Fix Class

- `cleanup`

## Acceptance Checks

- No invalid block-math nesting regressions.
- No image-text concatenation regressions.
- Stable table and paragraph structure in publish output.

## Override Relationship

- Temporary override allowed: `limited` for isolated layout placement edge cases.
- Trigger to promote core fix: repeated pattern in more than one subject.

## Decision

- Keep as active core candidate.
