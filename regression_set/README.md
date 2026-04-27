# Phase B Regression Set

This directory defines the fixed deterministic sample set for Phase B:

1. regression exam set
2. performance baseline
3. parser stabilization

Inventory file:

- `phase_b_inventory.json`

Coverage targets in this set:

- 2 chemistry files
- 2 physics files
- 2 math files
- 1 hard OLE/preview file
- 1 OMML-clean file

Each sample includes:

- source DOCX path
- expected artifact paths (HTML + QA JSON + notes)
- key verification notes

Runner:

- `scripts/regression/run_phase_b_regression.py`

The runner consumes this inventory and writes:

- per-sample artifacts
- timing baseline summary
- parser report outputs (via contract generation)

## Dedicated Answer Pipeline Regression Group

Answer pipeline v1 has a focused deterministic regression group:

- inventory: `answer_pipeline_inventory.json`
- runner: `scripts/regression/run_answer_pipeline_regression.py`

Run:

```bash
python3 scripts/regression/run_answer_pipeline_regression.py
```

Coverage includes:

1. MC local + summary agree
2. MC local vs summary conflict
3. True/false summary fill
4. Short-answer normalized equivalence
5. Essay rubric extraction (`R.` / `[R]`)
6. Override-applied case
7. No-summary but clear local extraction

## DOCX Export Regression Target

Phase G adds a dedicated DOCX export regression set:

- inventory: `docx_export_inventory.json`
- runner: `scripts/regression/run_docx_export_regression.py`

Run:

```bash
python3 scripts/regression/run_docx_export_regression.py
```

Coverage includes:

1. OMML-clean baseline
2. real sample with images and answer summary
3. harder MathType/OLE/preview-heavy sample

## Modern DOCX + OMML Smoke Gate

The official smoke gate for the modern path is the modern-only DOCX + OMML regression pack:

- inventory: `modern_docx_omml_inventory.json`
- smoke command: `python3 scripts/workflow/run_modern_docx_omml_smoke.py`
- scope: supported modern `.docx` inputs only
- purpose: enforce smoke-ready expectations for count, placement, Word reopenability, and OMML structure

The smoke command runs `regression_set/modern_docx_omml_inventory.json` through the current validator and prints:

```text
Summary: passed=<n> expected_failed=<n> unexpected_failed=<n> skipped=<n>
```

Gate rule:

- only `unexpected_failed > 0` fails the gate
- `expected_failed` is allowed for locked negative modern-scope cases
- `skipped` is visible in the report but does not fail the gate by itself

Required coverage:

1. OMML-native block equation
2. OMML-native inline equation
3. mixed block + inline supported case
4. supported multi-equation paragraph
5. negative modern-scope malformed or unsupported package case

Historical note:

- `docx_export_inventory.json` remains in the repo as historical prototype context
- DSMT4 / old MathType OLE cases are not part of the active modern regression pack

Suggested next implementation step:

- harden the modern DOCX + OMML mainline with generated-output structural validation before changing parser, patch engine, or exporter behavior

Run the generated-output gate:

```bash
python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py
```

Equivalent debug commands:

```bash
python3 scripts/workflow/generate_modern_docx_omml_output_manifest.py
python3 scripts/workflow/validate_modern_docx_omml_structure.py \
  --inventory out/modern-docx-omml-generated/modern_docx_omml_generated_outputs.json
```

This 4-case generated-output gate is the official precondition before product behavior changes. The wrapper prints the generated manifest path, basic DOCX openability summary, structural summary, and final validation status.

CI artifact preservation:

- workflow: `.github/workflows/modern-docx-omml-generated-output-gate.yml`
- uploaded artifact: `modern-docx-omml-generated-output-gate-report`
- preserved report path inside the run: `out/modern-docx-omml-generated/modern_docx_omml_generated_output_gate_report.json`
