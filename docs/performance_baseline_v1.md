# Performance Baseline v1 (Phase B)

Phase B baseline categories (seconds):

1. `unzip_load`
- `generate_sidecars.sh` extract time (`timings.tsv::extract`)
- plus converter DOCX load (`Conversion timings (ms)::DOCX load`)

2. `omml_conversion`
- converter OMML handling time (`Conversion timings (ms)::OMML handling`)

3. `sidecar_generation`
- wrapper run timing (`run.timings.tsv::sidecar-generation`)

4. `image_rendering`
- converter image/diagram rendering (`Conversion timings (ms)::Image/diagram rendering`)

5. `cleanup_sanitize`
- converter cleanup + publish sanitize:
  - `Conversion timings (ms)::HTML cleanup`
  - `Conversion timings (ms)::Publish sanitize`

6. `parser_json_build`
- contract parser build time from `parser_report.json::timings.parser_json_build_seconds`
- fallback: wall-clock runtime of contract generation step

7. `write_output`
- converter HTML write (`Conversion timings (ms)::HTML write`)

Runner:

- `scripts/regression/run_phase_b_regression.py`

Baseline outputs:

- `out/<run-name>/regression-sample-inventory.json`
- `out/<run-name>/baseline/performance-baseline.json`
- `out/<run-name>/baseline/performance-baseline.md`
