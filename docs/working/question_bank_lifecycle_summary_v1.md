# Question Bank Lifecycle Summary v1

This note compresses the question-bank integration docs into one lifecycle view.

## Purpose

Describe the path from DOCX ingest to preview, review, commit, and export without duplicating the implementation details in many separate docs.

## Lifecycle

1. upload / import DOCX
2. convert and parse
3. QA and preview
4. review / patch
5. commit into the bank
6. export assembled or random exam artifacts

## Main responsibilities

- ingestion orchestration
- parser to preview object mapping
- QA and publish gates
- review patch application
- commit into bank tables
- export of final DOCX / HTML artifacts

## Keep the boundary clear

- conversion concerns stay in the converter layer
- bank commit concerns stay in the bank layer
- export concerns stay in export / publish docs

## Replace / consolidate

- `question_bank_docx_ingest_module_architecture_spec.md`
- `docs/exam_assembly_fixed_vs_random_workflow_v1.md`
- `docs/exam_assembly_from_approved_bank_spec_v1.md`
- `docs/exam_assembly_required_metadata_v1.md`
- `docs/human_in_the_loop_review_implementation_handoff_v1.md`
- `docs/human_in_the_loop_review_phase1.md`
- `docs/parser_support_packages_v1.md`
- `docs/production_use_ready_v1_milestone.md`
- `question_bank_approved_import_v1.md`
- `question_bank_assembled_exam_docx_export_required_fields_v1.md`
- `question_bank_assembled_exam_docx_export_spec_v1.md`
- `question_bank_assembled_exam_docx_export_student_vs_teacher_v1.md`
- `question_bank_assembled_exam_docx_export_verification_v1.md`
- `question_bank_assembly_export_v1_milestone_20260411.md`
- `question_bank_assembly_persistence_decision_v1.md`
- `question_bank_assembly_record_listing_behavior_v1.md`
- `question_bank_assembly_usage_spec_v1.md`
- `question_bank_batch_import_and_reporting_v1.md`
- `question_bank_exam_preview_format_v1.md`
- `question_bank_fixed_exam_assembly_artifact_format_v1.md`
- `question_bank_fixed_exam_assembly_validation_behavior_v1.md`
- `question_bank_import_adapter_boundary_v1.md`
- `question_bank_import_dashboard_v1.md`
- `question_bank_import_readiness_policy_v1.md`
- `question_bank_phased_assembly_runtime_plan_v1.md`
- `question_bank_preview_and_docx_export_integration_v1.md`
- `question_bank_production_adapter_responsibilities_v1.md`
- `question_bank_production_approved_import_ops_v1.md`
- `question_bank_production_import_policy_v1.md`
- `question_bank_production_mapping_plan_v1.md`
- `question_bank_qb_c_preview_and_docx_triggers_v1.md`
- `question_bank_random_exam_assembly_artifact_format_v1.md`
- `question_bank_random_exam_assembly_determinism_validation_v1.md`
- `question_bank_random_exam_assembly_validation_behavior_v1.md`
