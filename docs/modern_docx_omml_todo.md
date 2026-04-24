# Modern DOCX + OMML TODO

This note turns the current support boundary into an execution checklist for the modern `.docx` + OMML mainline.

Reference:

- [README.md](../README.md)
- [Support Scope Policy](./support_scope_policy.md)

## Input Scope And Acceptance

- Keep modern `.docx` as the supported input type.
- Prefer native OMML whenever the document already contains it.
- Support only equation content that the current pipeline converts stably to OMML.
- Preserve equation count and equation placement after round-trip.
- Reopened documents must stay safe to edit in Word.
- Block equations:
  - keep native OMML intact when already present
  - ensure block-equation placement survives round-trip
- Inline equations:
  - keep inline OMML stable in text flow
  - do not introduce legacy MathType/OLE recovery as an inline default
- Multi-equation paragraphs in supported modern scope:
  - preserve order
  - preserve count
  - preserve safe paragraph structure
  - fail clearly if a paragraph is outside the supported shape

## Regression Corpus

- Maintain a small modern `.docx` corpus with native OMML coverage.
- Keep samples that exercise:
  - block equations
  - inline equations
  - mixed text plus equation paragraphs
  - multi-equation paragraphs that are already supported
- Keep legacy DSMT4 / old MathType OLE samples only as frozen historical reference, not as active regression targets.
- Add new samples only when they represent the modern OMML mainline or a clearly supported edge case.

## Regression Pack Requirements

- Define one named modern-path regression pack for supported `.docx` inputs only.
- The pack should contain at least:
  - one OMML-native block-equation sample
  - one OMML-native inline-equation sample
  - one supported mixed block + inline sample
  - one supported multi-equation paragraph sample
  - one negative modern-scope sample for malformed or clearly unsupported package handling
- For each sample, keep:
  - source `.docx`
  - expected equation count
  - expected block vs inline placement summary
  - expected reopenability status
  - expected supported vs out-of-scope classification
- Keep the pack small enough for smoke use, but stable enough to catch placement regressions.
- Do not add legacy DSMT4 or old `.doc` files to this pack.

## Golden Files And Invariants

- Golden files should capture:
  - equation count
  - equation order
  - equation placement
  - reopenability in Word
- Output DOCX acceptance:
  - Word reopens safely
  - equation count is preserved
  - block placement is preserved
  - inline placement is preserved
  - `m:oMath` / `m:oMathPara` structure remains valid for supported outputs
- OMML validation:
  - output must remain valid OMML for supported cases
  - native OMML should not be rewritten unnecessarily
  - generated OMML should preserve the existing document structure where possible
- Invariants:
  - supported files stay supported on rerun
  - unsupported files fail clearly
  - diagnostics distinguish structure problems from legacy format problems

## Logging And Diagnostics

- Report supported vs out-of-scope inputs explicitly.
- Explain why a file is out of scope instead of silently trying legacy recovery.
- Keep diagnostics short and actionable:
  - native OMML present
  - supported modern equation content
  - unsupported legacy format
  - malformed or broken package
- Avoid logging that suggests legacy DSMT4 is still an active support target.

## CLI And UX Expectations

- Keep the main command line focused on modern `.docx` flows.
- Make the supported path obvious in help text and README examples.
- Emit a clear error for `.doc` and broken pseudo-`.docx` inputs.
- Keep legacy recovery flows out of the default UX.

## Smoke Workflow

- Use a small OMML-first smoke set as the mainline regression gate.
- Run smoke tests against the modern DOCX + OMML path only.
- Verify:
  - input opens cleanly
  - equations survive round-trip
  - output reopens in Word
  - output keeps valid `m:oMath` / `m:oMathPara` structure
  - no legacy recovery path is required

## Backlog Priorities

1. Preserve modern DOCX + OMML behavior.
2. Expand coverage only for supported equation shapes that already convert stably.
3. Improve diagnostics for unsupported modern inputs.
4. Keep legacy DSMT4 material frozen as historical evidence.
5. Avoid any new roadmap item for old MathType OLE unless the support boundary changes explicitly.

## Non-Goals

- Do not reintroduce legacy DSMT4 as a product target.
- Do not expand the mainline to old `.doc` equation workflows.
- Do not treat historical DSMT4 reports as current roadmap items.
- Do not change patch engine behavior, Java matching, usable-sidecar filtering, or parser/converter defaults in this checklist.

## Done Definition

- Modern `.docx` with native OMML stays stable.
- Supported equation content round-trips safely and reopens in Word.
- Block, inline, and supported multi-equation paragraphs behave consistently.
- Unsupported legacy files fail clearly and are identified as out of scope.
- Regression and smoke runs stay aligned with the modern DOCX + OMML mainline.
