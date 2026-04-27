# DSMT4 Taxonomy Baseline

Frozen historical baseline only. This document is kept for legacy reference and is not the active product roadmap or support target.

## Current Labels

- `METADATA_ONLY_FULL_END_ONLY`: dominant unsupported subtype line.
- `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`: narrow converter/classification-boundary follow-up line.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`: taxonomy-only near-`FULL_END_ONLY` variant, not yet proven as a separate failure mode.

## Baseline Statements

- `METADATA_ONLY_FULL_END_ONLY` is the main investigation line for the unsupported subtype shape.
- `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY` is the best current narrow follow-up for converter/classification-boundary evidence.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` stays in taxonomy only because the current evidence is a near-`FULL_END_ONLY` variant with the same metadata-only `full -> end` tail, not a distinct failure mode.

## Current Non-Goals

- Do not open a production fix branch.
- Do not change the DOCX patch engine.
- Do not change Java matching.
- Do not change usable-sidecar filtering.
- Do not change converter logic.
- Do not change parser/converter default behavior.
- Do not merge any default parser/converter decode rule without new parser-stage/body evidence.

## Recommended Next Branch

- If work continues, the next branch should be a narrow upstream converter/classification-boundary investigation for `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`.
- `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER` should remain taxonomy-only unless new evidence creates a stable split from `METADATA_ONLY_FULL_END_ONLY`.

## Current Recommendation

- Do not open a production fix yet.
- If any follow-up is needed, prefer only a narrow investigation for `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`.
- Otherwise, treat the taxonomy as frozen until new corpus, new reference evidence, or new parser-stage/body evidence appears.

## Why No Production Fix Yet

- The dominant unsupported line still needs parser-input interpretation investigation.
- The converter-boundary line is real, but the current evidence is diagnostic, not a product fix.
- The near-`FULL_END_ONLY` line has multiple structural signatures, but they all remain metadata-only and do not prove a separate failure mode.

## Canonical Evidence

- Spec/reference semantics note: [dsmt4_mtef_spec_reference_note.md](./dsmt4_mtef_spec_reference_note.md)
- Deep-audit for `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`: [dsmt4_metadata_only_no_renderable_body_other_deep_audit.md](./dsmt4_metadata_only_no_renderable_body_other_deep_audit.md)
- Deep-audit for `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`: [empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md](./empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md)
- Underscore-group taxonomy audit: [dsmt4_underscore_big_group_audit_2026-04-23.md](./dsmt4_underscore_big_group_audit_2026-04-23.md)
- Full `in/*` corpus audit: [dsmt4_full_in_corpus_audit_2026-04-23.md](./dsmt4_full_in_corpus_audit_2026-04-23.md)
- Source-local split note for `_30_Li_2025`: [dsmt4_30_li_2025_source_local_split.md](./dsmt4_30_li_2025_source_local_split.md)
- Taxonomy lines report: [dsmt4_taxonomy_lines_report.md](./dsmt4_taxonomy_lines_report.md)

## Handoff

- Stable baseline: yes
- Production fix branch now: no
- Next investigation candidate: `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`
- Next parser boundary if reopened: `CONVERTER_CLASSIFICATION_BOUNDARY`
