# DOCX Export Regression Target v1

This document defines the active regression-pack requirements for the modern `.docx` + OMML path.

## Active Target

The active regression target is a small modern-only pack for supported `.docx` inputs. Regression pack v1 is now the official smoke gate for the modern DOCX + OMML path.

Run the gate with:

```bash
python3 scripts/workflow/run_modern_docx_omml_smoke.py
```

Expected success summary shape:

```text
Summary: passed=<n> expected_failed=<n> unexpected_failed=0 skipped=<n>
```

Gate rule:

- only `unexpected_failed > 0` fails the gate
- `expected_failed` is reserved for locked negative modern-scope cases
- `skipped` is reported for visibility and does not fail the gate by itself

Coverage categories:

1. OMML-native block equation
2. OMML-native inline equation
3. mixed block + inline supported case
4. supported multi-equation paragraph
5. negative modern-scope case for malformed or unsupported package handling

## Machine-Readable Inventory

The planning scaffold for this pack lives at:

- `regression_set/modern_docx_omml_inventory.json`
- `scripts/workflow/run_modern_docx_omml_smoke.py`

Historical export inventory remains in the repo for older prototype context:

- `regression_set/docx_export_inventory.json`

That historical inventory is not the active roadmap for this phase.

## Required Per-Case Metadata

Each modern-pack case should define:

- source `.docx` path
- supported vs out-of-scope classification
- expected total equation count
- expected block equation count
- expected inline equation count
- expected placement summary
- expected Word reopenability status
- expected `m:oMath` / `m:oMathPara` structure status
- notes describing the purpose of the case

## Output Acceptance Criteria

For supported cases, exported `.docx` output passes only if:

1. Word reopens the file safely
2. equation count is preserved
3. block placement is preserved
4. inline placement is preserved
5. `m:oMath` / `m:oMathPara` structure is valid

## Pack Constraints

- keep the pack small enough for smoke use
- prefer modern native-OMML samples first
- do not add DSMT4, old MathType OLE, or old `.doc` files
- treat malformed or unsupported `.docx` cases as modern-scope negatives, not as legacy-support prompts

## Immediate Next Use

This target is intended to drive:

- official smoke gating for modern DOCX + OMML changes
- structural validation for output OMML in supported generated `.docx` files
- count and placement regression checks for supported modern files

Suggested next implementation step:

- harden the modern mainline by validating generated DOCX output structure against the same count, placement, and `m:oMath` / `m:oMathPara` expectations before changing product behavior
