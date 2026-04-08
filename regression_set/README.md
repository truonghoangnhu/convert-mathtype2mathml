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
