# Support Scope Policy

This document is the canonical support-boundary note for the repository.

## Supported input scope

- modern `.docx` documents
- native OMML equations already stored in WordprocessingML
- equation content that the current pipeline converts stably to OMML
- repository workflows that stay on the modern DOCX + OMML path

## Out of scope

- legacy DSMT4 / old MathType OLE as an official product target
- old `.doc` equation workflows
- malformed pseudo-`.docx` packages that do not behave like normal DOCX ZIP containers
- reopening legacy degenerate equation investigations as default roadmap work

## Current project focus

- keep modern `.docx` support stable
- prioritize native OMML
- preserve one mainline equation path centered on OMML
- support only equation formats that the current pipeline already converts stably to OMML

## Migration guidance for legacy files

- reopen and resave legacy files as modern `.docx` before processing them here
- replace old MathType / OLE content with native OMML where practical
- treat legacy `.doc`, DSMT4, and old MathType OLE content as migration work outside the official support boundary
- use the archived DSMT4 notes only as historical reference when triaging old corpora

## Non-goals

- do not expand official support back to legacy DSMT4
- do not add new legacy recovery work just because historical scripts still exist in the repo
- do not treat historical audit output as the current roadmap
- do not open production-fix work for legacy DSMT4 from this policy alone

## Historical baseline

The repository keeps prior DSMT4 investigation material as frozen historical baseline, not as active roadmap:

- [dsmt4_taxonomy_baseline.md](./dsmt4_taxonomy_baseline.md)
- [dsmt4_mtef_spec_reference_note.md](./dsmt4_mtef_spec_reference_note.md)
- [dsmt4_taxonomy_lines_report.md](./dsmt4_taxonomy_lines_report.md)
- [dsmt4_full_in_corpus_audit_2026-04-23.md](./dsmt4_full_in_corpus_audit_2026-04-23.md)
- [dsmt4_metadata_only_no_renderable_body_other_deep_audit.md](./dsmt4_metadata_only_no_renderable_body_other_deep_audit.md)
- [empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md](./empty_generated_sidecar_with_renderable_body_investigation_10_toan_hcm_2026.md)
- [dsmt4_30_li_2025_source_local_split.md](./dsmt4_30_li_2025_source_local_split.md)
- [dsmt4_underscore_big_group_audit_2026-04-23.md](./dsmt4_underscore_big_group_audit_2026-04-23.md)

## Mainline message

- modern DOCX + OMML is the mainline
- legacy DSMT4 is no longer a product target
