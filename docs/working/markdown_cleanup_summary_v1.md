# Markdown Cleanup Summary v1

This file is a compact merge map for the working and root-level `.md` docs in this repository.
It is meant to be the pre-removal reference: review this first, then delete only the files that are
explicitly marked as merge candidates or removals.

## Keep As-Is

These docs already serve as stable reference points and should stay separate.

- `README.md`
- `docs/parser_report_v1.md`
- `docs/output_contract_v1.md`
- `docs/performance_baseline_v1.md`
- `docs/performance_gate_v1.md`
- `docs/publish_gates_matrix.md`
- `docs/override_manifest_v1.md`
- `docs/production_use_ready_v1_milestone.md`
- `docs/contract_compatibility_gate_v1.md`
- `docs/docx_export_architecture_spec_v1.md`
- `docs/docx_export_direction_v1.md`
- `docs/docx_export_failure_policy_v1.md`
- `docs/docx_export_parity_report_v1.md`
- `docs/docx_export_regression_target_v1.md`
- `docs/docx_export_styling_readiness_v1.md`

## Merge Into Fewer Files

These are the groups that can be consolidated into one shorter note per theme.

Merged files:

- `docs/working/README.md`
- `docs/working/answer_pipeline_summary_v1.md`
- `docs/working/core_runtime_orchestration_summary_v1.md`
- `docs/working/question_bank_lifecycle_summary_v1.md`
- `docs/working/chemistry_physics_cleanup_summary_v1.md`
- `docs/working/workflow_milestones_summary_v1.md`

## Remove After Merge

These are the files most likely to become redundant once the grouped summaries above exist.

- root-level drafts already superseded by `docs/working/README.md`
- duplicate root-level topic notes that were moved under `docs/working/`
- any working note whose content is fully represented by one grouped summary above

## Suggested Next Step

If you want a smaller repo doc set, keep the files in `Keep As-Is`, then replace the grouped files with one summary per option:

- one answer pipeline note
- one runtime/orchestration note
- one question-bank lifecycle note
- one chemistry/physics cleanup note
- one milestones index
