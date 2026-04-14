# Core Runtime and Orchestration Summary v1

This note consolidates the runtime invariants and core render policy for the conversion pipeline.

## Purpose

Keep convert orchestration deterministic, single-input, and output-safe.
Keep OMML, MathType, and image handling in the core layer rather than scattering fixes into subject-specific docs.

## Core invariants

- single explicit input by default
- recursive discovery only by explicit opt-in
- outputs must never be rediscovered as inputs
- one canonical input path = one active conversion job
- QA and cleanup must never trigger a new conversion pass
- cleanup must not delete current referenced outputs

## Core policy areas

- OMML parsing, MathML conversion, and wrapper rendering
- MathType / DSMT4 resolution and fallback policy
- generic image / diagram classification and fallback behavior
- subject profile selection and mapping

## Replace / consolidate

- `core_omml_mathtype_image_policy.md`
- `core_vs_subject_mapping_and_codex_run.md`
- `generic_inline_image_whitespace_trim_crop_policy.md`
- `orchestration_invariants.md`
- `subject_profiles_spec_v1.md`

