# Full Regression Runner v1

This note documents the unified one-command regression entrypoint.

## Purpose

- run the major regression groups in a single pass
- keep the underlying group runners unchanged
- produce one aggregated verdict and one aggregated report
- make the DOCX openability caveat visible instead of hiding it

## Included Groups

1. Phase B regression
2. answer-pipeline regression
3. DOCX export regression

## Runner

Use:

```bash
python3 scripts/regression/run_full_regression.py
```

Optional flags:

- `--groups phase-b answer-pipeline`
- `--groups all`
- `--run-name my-full-regression`
- `--output-root out`
- `--fail-fast`

Default behavior is run-all in sequence.

## Verdict Mapping

The aggregated verdict uses three states:

- `passed`
- `passed_with_review`
- `failed`

Rules:

- any hard failure in a child group makes the full run `failed`
- any child group that only passes with review signals makes the full run `passed_with_review`
- otherwise the full run is `passed`

## Report Output

The runner writes:

- `full-regression-report.json`
- `full-regression-report.md`

They are created under:

- `out/<run-name>/`

Child report paths are linked from the aggregated report.

## Child Report Locations

The current layout is:

- `out/<run-name>/phase-b/baseline/performance-baseline.json`
- `out/<run-name>/answer-pipeline/answer-pipeline-regression-report.json`
- `out/<run-name>/docx-export/docx_export_regression_report.json`

## DOCX Openability Caveat

The DOCX export regression still surfaces the LibreOffice/`soffice` openability signal explicitly. In this workspace it is environment-sensitive, so the aggregated report keeps that caveat visible in the DOCX group summary instead of folding it away.
