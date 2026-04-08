# Contract Compatibility Gate v1

Purpose: detect schema drift and incompatible output contract changes automatically.

## Config

- `scripts/contracts/contract_compatibility_v1.json`
- schema: `contract_compatibility_gate.v1`

Checks include:

1. required artifact files exist
2. expected `schema_version` per artifact
3. expected `artifact_type` per artifact
4. required top-level keys per artifact
5. consistent `bundle_id` across artifacts
6. required manifest artifact map entries
7. required manifest enum values

## Runtime usage

CLI:

```bash
python3 scripts/contracts/check_contract_compatibility.py \
  --contract-dir <contract_dir> \
  --config scripts/contracts/contract_compatibility_v1.json
```

Runner integration:

- `scripts/regression/run_phase_b_regression.py`

Contract gate runs per sample and records:

- `contract_gate.passed`
- `contract_gate.errors`
- `contract_gate.summary`

With `--enforce-gates` (default), incompatibility causes run failure.
