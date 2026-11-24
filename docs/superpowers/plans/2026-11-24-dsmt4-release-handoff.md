# DSMT4 release handoff implementation plan

> Execute the four handoff steps explicitly approved by the project owner in this chat.

**Goal:** Publish the scoped DSMT4 migration release with portable acceptance evidence and a tested delivery archive.

**Spec:** `docs/dsmt4_migration_acceptance.md`, final status 2026-11-24, and the owner's approved steps 1–4.

**Constraints:** Keep converter behavior unchanged; preserve 238 accepted / 27 needs_review (18 retained OLE, 9 presentation limitations). Do not publish source exam documents or redistribute the external transpect runtime. Preserve unrelated `.claude/` files. Use a dedicated branch in the current clean checkout so the existing local evidence remains available.

- [x] Snapshot the 265-row ledger, summary, 27 exceptions, source/output hashes and external-runtime versions under `docs/acceptance/dsmt4-2026-11-24/`; validate counts and hashes.
- [x] Close D2 and D4 as completed assessment with explicit exceptions; replace the ignored ledger reference with the versioned snapshot.
- [x] Add concise delivery instructions and a reproducible bundle command containing the built JAR, scripts, documentation, sample fixtures, provenance and checksums.
- [ ] Run Maven, both Python suites, generated-output gate and modern smoke; extract the bundle into a fresh directory with spaces and run Word patch and LibreOffice Math preparation examples there.
- [ ] Review, commit, push, merge the delivery PR after required checks pass, then tag and publish `dsmt4-migration-2026.11.24` with the verified bundle, standalone JAR and checksums.

Completion means the release assets are downloadable and their hashes match the locally tested artifacts. Acceptance applies only to the identified five-exam subset; this release does not claim complete conversion or Writer DOCX parity.

Review: an independent reviewer reconciled all 265 rows and the 27 exceptions. The root START_HERE link was corrected to point to the guide under docs/.
