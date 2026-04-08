# DOCX Export Direction v1 (Phase C)

## Decision Statement

The export direction is fixed as:

1. MathML is the internal canonical math representation.
2. DOCX export should map canonical math through:
- `MathML -> OMML -> WordprocessingML`
3. The exporter will be implemented after current stabilization milestones, not in Phase C.

This removes ambiguity for later implementation.

Detailed architecture mapping is specified in:

- `docs/docx_export_architecture_spec_v1.md`

## Why This Direction

- Current pipeline already converges equations to MathML with good quality.
- Keeping one canonical math form avoids split logic between OMML and MathType/OLE remnants.
- DOCX requires OMML for native Word equation fidelity.

## Planned Data Flow

1. Source artifacts:
- `exam_bundle.json`
- `question_bank_items.json`
- reviewed HTML fragments/assets

2. Export assembly:
- Build normalized content blocks from canonical HTML+MathML
- Transform MathML nodes into OMML blocks
- Write WordprocessingML (`document.xml`, relationships, media parts)
- Package as `.docx`

3. Validation:
- Open in Word/LibreOffice
- Verify equation fidelity, section ordering, tables, images, and answer blocks

## Scope Boundaries

Phase C includes only decision and policy.

Phase C does not include:

- full exporter implementation
- question_bank integration
- redesign of converter architecture

## Non-goals

- Reconstruct legacy MathType OLE objects in exported DOCX.
- Keep preview-image math as canonical math.
- Introduce a second canonical math representation.

## Risks and Mitigations

1. Risk: MathML features not mapped cleanly to OMML.
- Mitigation: keep explicit unsupported-token inventory and fallback policy.

2. Risk: Inline/display math layout drift in exported DOCX.
- Mitigation: keep placement metadata and dedicated export rendering tests.

3. Risk: Asset placement regressions.
- Mitigation: use existing placement classes (`inline`, `display`, `context-right`, `centered`, `table-cell`) as exporter input hints.

## Minimal Prototype Status

No exporter prototype is added in Phase C.
This is intentional to keep this phase document/policy-first.

## Entry Criteria For Export Implementation (Post-Phase C)

- Phase A/B contracts and parser are stable enough for review flow.
- Override policy is available for controlled edge cases.
- Core promotion path is documented to reduce repeated one-off patches.

## Exit Criteria For First Export Prototype

- Round-trip sample set (at least one chemistry, one physics, one math) opens in Word.
- Equations remain editable native Word equations (OMML-backed).
- No fallback to preview images for equations that are canonical MathML.
- QA checklist for exported DOCX is documented.
