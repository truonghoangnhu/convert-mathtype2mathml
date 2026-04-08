# Performance Gate v1

Purpose: enforce baseline performance thresholds and fail clearly on regressions.

## Config

- `regression_set/performance_gate_v1.json`
- schema: `performance_gate.v1`

## Aggregate thresholds

Per timing category supports:

- `p90_seconds_max`
- `total_seconds_max`

Categories:

- `unzip_load`
- `omml_conversion`
- `sidecar_generation`
- `image_rendering`
- `cleanup_sanitize`
- `parser_json_build`
- `write_output`

## Sample thresholds

Per-sample limits use:

- `sample_limits.<category>.seconds_max`

Category-specific sample overrides are supported.

## Runtime wiring

Performance gate is evaluated in:

- `scripts/regression/run_phase_b_regression.py`

Failures are recorded in baseline report under `gates.failures` with:

- gate name
- scope (`aggregate` or `sample`)
- metric
- actual value
- limit

With `--enforce-gates` (default), performance gate failures fail the run.
