# Output Contract v1

This document defines the deterministic JSON artifacts generated for each converted bundle.

## Schema Version

- `schema_version`: `output_contract.v1`

## Artifacts

Each bundle emits deterministic contract files in the contract output folder:

1. `manifest.json`
2. `exam_bundle.json`
3. `question_bank_items.json`
4. `qa.json`
5. `parser_report.json`
6. `override_audit.json`

## Stable Enums

- `output_modes`: `internal`, `publish`
- `publish_verdicts`: `safe_to_publish`, `needs_review`, `blocked`
- `qa_severities`: `info`, `warning`, `error`, `blocker`
- `question_types`: `unknown`, `single_choice`, `multiple_choice`, `true_false`, `short_answer`, `essay`
- `asset_roles`: `equation`, `diagram`, `chart`, `chemical-diagram`, `generic-image`, `unknown-preview`
- `placements`: `inline`, `display`, `context-right`, `context-below`, `centered`, `table-cell`, `unknown`

## Determinism Rules

- JSON is written with deterministic key ordering (`sort_keys=true`).
- Ordering-sensitive lists are explicitly sorted.
- Bundle identity is a content-derived hash (`bundle_id`) from source and output fingerprints.
- No runtime timestamp fields are required in contract files.

## File Shapes

### `manifest.json`

Contains:
- contract metadata (`schema_version`, `artifact_type`, `bundle_id`)
- source pointers (`docx_path`, `html_path`, `qa_source_path`, hashes)
- publish summary (`publish_verdict`, `publish_gate_summary`)
- artifact file map
- enum definitions

### `exam_bundle.json`

Contains:
- bundle metadata
- source pointers
- summary metrics (`total_mathml_formulas`, `total_previews`, verdict, unresolved count)
- per-exam metrics (`exams`)
- exam-level answer summary extraction output (`answer_summary`)
- answer reconciliation QA aggregate (`answer_qa_summary`)
- total extracted question item count

### `question_bank_items.json`

Contains:
- bundle metadata
- deterministic list of extracted question stubs:
  - `item_id`
  - `exam_id`
  - `question_number`
  - `question_type`
  - `placement`
  - `asset_roles`
  - `prompt_preview`
  - source line pointer
- per-question answer reconciliation fields:
  - `answer_key`
  - `answer_sources`
  - `reconciliation`
  - `answer_detection`
  - `rubric`
  - `rubric_detection`
  - `qa_flags`

### `qa.json`

Contains:
- bundle metadata
- normalized publish gate outputs:
  - `publish_verdict`
  - `publish_gate_summary`
  - `publish_gate_findings`
- copied QA aggregates:
  - `totals`
  - `count_by_type`
  - `per_exam`
  - `unresolved_objects`
- override runtime summary:
  - `override_audit.manifest_id`
  - `override_audit.applied_count`
  - `override_audit.skipped_count`
  - `override_audit.failed_count`
- source QA report pointer
- answer QA payload:
  - `answer_summary`
  - `answer_qa_summary`
  - `answer_qa_issues`

### `parser_report.json`

Contains:
- parser metadata (`schema_version`, `artifact_type`, `bundle_id`)
- parser summary (`sections_count`, `question_count`, confidence stats)
- answer summary extraction metadata (`answer_summary`)
- answer reconciliation aggregate (`answer_qa_summary`)
- section-level parser aggregates
- question-level parse confidence and warning codes
- question-level answer reconciliation fields (answer key/sources/status/flags)
- parser warnings and parser-build timing

### `override_audit.json`

Contains:
- override runtime metadata:
  - `manifest_provided`
  - `manifest_path`
  - `manifest_id`
- per-override audit records:
  - `override_id`
  - `action`
  - `status` (`applied` | `skipped` | `failed`)
  - `matched_count`
  - `mutated_count`
  - `reason`
- aggregate action counters in `summary`
