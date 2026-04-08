# DOCX Export Styling Readiness v1

This note defines the minimum styling direction for the next DOCX export phase.

## Current Recommendation

Keep the current prototype on built-in WordprocessingML styles first:

- `Normal`
- `Heading 1`
- `Heading 2`
- `List Paragraph`
- `Table Grid`
- equation paragraph conventions

## Why This Is the Right Default

- deterministic
- low coupling
- easy to debug against raw DOCX XML
- avoids template drift while export logic is still stabilizing

## Next Phase Readiness

Before adding a richer template, define defaults for:

- document title
- section headings
- question blocks
- answer appendix
- image sizing
- table spacing

## Minimal Template Plan

The next step after the prototype should be a hybrid model:

- keep the exporter logic
- add a small seed DOCX template only when formatting requirements justify it

That keeps formatting changes isolated from content reconstruction.

