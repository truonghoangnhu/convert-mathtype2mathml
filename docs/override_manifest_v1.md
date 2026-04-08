# Override Manifest v1

This document defines the controlled override mechanism for edge cases.

Scope of this version:

- Spec and validation format
- Policy for when overrides are allowed
- Policy for when core/spec fix is required instead

It does not redesign the converter pipeline.

## Schema

- `schema_version`: `override_manifest.v1`
- `manifest_id`: stable identifier
- `description`: optional text
- `source`: source binding metadata
- `overrides`: list of override records

### Source

`source` fields:

- `docx_path` (optional)
- `docx_sha256` (optional)
- `subject`: `generic | chemistry | physics | math | biology`
- `output_mode`: `internal | publish`

## Override Actions

Each override record includes:

- `id` (required, unique)
- `enabled` (optional, default true)
- `action` (required)
- `match` (required for non-global actions)
- `value` (required)
- `reason` (required)
- `owner` (required)
- `ticket` (optional, required for publish exceptions)
- `expires_on` (optional, required for publish exceptions)

Supported `action` values:

1. `asset_visibility`
- Supports keep/suppress image.
- `value.visibility`: `keep | suppress`

2. `asset_role_override`
- Overrides asset role.
- `value.role`: `equation | diagram | chart | chemical-diagram | generic-image | unknown-preview`

3. `placement_override`
- Overrides placement.
- `value.placement`: `inline | display | context-right | context-below | centered | table-cell | unknown`

4. `text_patch`
- Deterministic text patch.
- `value.target`: `html | visible_text | stem_html | solution_html`
- `value.match_mode`: `literal | regex`
- `value.find`: source pattern
- `value.replace`: replacement text
- `value.max_replacements` (optional, positive integer)

5. `publish_exception`
- Controlled publish-gate exception.
- `value.metric`: gate metric key
- `value.allow_if_lte`: numeric threshold
- `value.severity_override` (optional): `info | warning | error | blocker`
- Requires `ticket` and `expires_on`.

6. `answer_override`
- Manual answer source for reconciliation.
- Participates as `manual_override` in `answer_sources` (does not erase original evidence).
- `value.mode`: `single_choice | boolean_group | short_answer | rubric | none`
- For `single_choice`:
  - `value.value`: `A | B | C | D`
- For `boolean_group`:
  - `value.subanswers`: object like `{"a": true, "b": false, ...}`
- For `short_answer`:
  - `value.accepted_answers` and/or `value.value`
- For `rubric`:
  - `value.rubric_text` and/or `value.blocks`

## Match Object

`match` may include the following selectors:

- `exam_id`
- `question_id`
- `question_number`
- `asset_id`
- `asset_src`
- `asset_src_contains`
- `prog_id`
- `source_ext`
- `fallback_type`
- `css_class_contains`

At least one selector is required for non-global operations.

## Policy: When Override Is Allowed

Override is allowed for narrow, deterministic edge cases:

- A one-off asset keep/suppress decision.
- A one-off role/placement correction where core classifier is otherwise stable.
- A deterministic text corruption patch in a limited scope.
- A temporary publish exception with owner + ticket + expiry.

## Policy: When Core/Spec Fix Is Required

Do not use override as primary fix when:

- Same issue pattern appears in 2+ subjects.
- Same issue pattern appears in 3+ exams of one subject.
- The change belongs to shared parser/classifier/render/cleanup logic.
- The patch changes math semantics or answer correctness.

In these cases, create/update a core promotion candidate note and implement in core/spec.

## Governance Rules

- Every publish exception must have `ticket` and `expires_on`.
- Expired exceptions must be removed or converted to proper core/spec fixes.
- Overrides must be versioned in repo and reviewed.
- Override IDs are immutable once published.

## Example Manifest

See:

- `overrides/override_manifest.example.json`

## Validation Tool

A lightweight validator is provided:

```bash
python3 scripts/overrides/validate_override_manifest.py \
  --manifest overrides/override_manifest.example.json
```

It validates structure and action-specific requirements.
