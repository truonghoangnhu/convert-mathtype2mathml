# Modern DOCX + OMML Roadmap

This document defines the active technical roadmap for the modern `.docx` + OMML path.

References:

- [README.md](../README.md)
- [Support Scope Policy](./support_scope_policy.md)
- [DOCX Export Regression Target v1](./docx_export_regression_target_v1.md)

## Phase Statement

The current phase is:

- modern `.docx` only
- OMML only for native Word equation handling
- docs, planning, and regression/test scaffolding first
- minimal product logic changes unless required for modern-path clarity

## Active Scope

- supported input is modern `.docx`
- supported equations are native OMML or equation content that already converts stably to OMML
- supported round-trip target is output `.docx` that stays on valid WordprocessingML + OMML structure
- supported diagnostics distinguish valid modern inputs from malformed packages and out-of-scope legacy inputs

## Frozen Historical Background

The following remain historical background only:

- DSMT4 investigation notes
- old MathType OLE recovery work
- old `.doc` equation workflows
- legacy-heavy export targets that were useful for prior audits but are not part of the active roadmap

They may be cited for background, but they are not active backlog items and should not be reopened by default.

## Workstreams

### 1. Scope and documentation

- keep README and support docs explicit about modern `.docx` + OMML only scope
- keep legacy references marked as frozen historical background
- keep CLI/help examples aligned with the modern path

### 2. Regression-pack scaffolding

- define one named regression pack for supported modern `.docx` files only
- keep the pack small, deterministic, and suitable for smoke use
- store machine-readable expectations per sample
- keep unsupported and malformed samples separate from legacy-format samples

### 3. Output acceptance scaffolding

- define acceptance checks for exported `.docx`
- define the minimum metadata needed to verify count, placement, and OMML structure
- keep validation language Word-oriented rather than legacy-recovery-oriented

### 4. Minimal product work only when needed

- only change converter/export logic when a modern-path ambiguity blocks acceptance or regression work
- avoid reopening parser, patch engine, or sidecar behavior unless directly required by modern-path clarity

## Regression Pack Requirements

The active regression pack must cover supported modern `.docx` files only. Regression pack v1 is the official smoke gate for the modern DOCX + OMML path.

Run:

```bash
python3 scripts/workflow/run_modern_docx_omml_smoke.py
```

Expected success summary shape:

```text
Summary: passed=<n> expected_failed=<n> unexpected_failed=0 skipped=<n>
```

Gate rule:

- only `unexpected_failed > 0` fails the gate
- `expected_failed` is allowed for locked negative modern-scope cases
- `skipped` is reported for visibility and does not fail the gate by itself

Required sample categories:

1. one OMML-native block-equation sample
2. one OMML-native inline-equation sample
3. one mixed block + inline sample that remains within the supported path
4. one supported multi-equation paragraph sample
5. one negative modern-scope sample for malformed or clearly unsupported `.docx` package handling

Each pack entry must record:

- `case_id`
- source `.docx` path
- expected supported vs out-of-scope classification
- expected equation count
- expected block equation count
- expected inline equation count
- expected ordering or placement summary
- expected Word reopenability status
- expected OMML structure status
- notes describing why the sample belongs in the pack

Pack rules:

- do not add DSMT4 or old MathType OLE files
- do not add old `.doc` files
- do not use historical legacy cases as the default smoke gate
- keep the pack small enough to run frequently

## Output DOCX Acceptance Criteria

For supported modern-path outputs, acceptance means all of the following:

1. Word reopens the exported `.docx` safely
2. equation count is preserved
3. block equation placement is preserved
4. inline equation placement is preserved
5. `m:oMath` and `m:oMathPara` structure is valid for the equations owned by the pipeline

Interpretation notes:

- "count preserved" means no equation is dropped, duplicated, or converted into a non-equation placeholder within the supported path
- "placement preserved" means block equations remain block-level and inline equations remain inline in text flow
- "valid structure" means `m:oMath` and `m:oMathPara` are used in the correct contexts and do not leave malformed WordprocessingML around equation boundaries

## Test Scaffolding Requirements

Initial scaffolding should focus on metadata-driven validation before deeper implementation work.

Needed first:

- one machine-readable regression inventory for the modern pack
- a validator shape that can compare expected count and placement against produced artifacts
- a structural check for `m:oMath` and `m:oMathPara` usage in output `.docx`
- a clear place to record Word reopenability results

Nice-to-have after the scaffold exists:

- fixture-level extraction of equation summaries from `word/document.xml`
- per-case golden summaries for count and placement
- generated-output structural validation against the same modern-pack expectations

## Backlog Order

1. keep the official smoke gate green for every modern DOCX + OMML change
2. add structural validation for generated `.docx` outputs using `m:oMath` and `m:oMathPara`
3. extend count and placement verification from source fixtures to supported generated outputs
4. make only the smallest product changes needed to satisfy the modern acceptance checks

## Definition Of Done For This Phase

- README and support docs clearly state the modern `.docx` + OMML only scope
- one technical roadmap exists for the modern path
- one official smoke gate exists for supported modern `.docx` files
- output `.docx` acceptance criteria are explicit and testable
- DSMT4 and other legacy work are clearly marked as frozen historical background
