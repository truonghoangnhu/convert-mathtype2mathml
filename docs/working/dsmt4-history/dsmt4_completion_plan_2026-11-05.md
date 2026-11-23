# DSMT4 verified-scope completion plan

Spec: `docs/support_scope_policy.md`, the user's OLE → MTEF → MathML → Word/Math requirements, and `codex_dsmt4_writer_mathml_review_2026-11-05.md`.

Continue inline in the existing feature checkout as requested. Preserve all previous changes, source/ZIP/fixtures and old evidence. No commit, push, merge or new worktree. No universal-decoder or full-acceptance claim.

- [x] Reproduce/fix invisible CGJ/variation-selector-only formulas in Java/Python; keep selectors beside visible bases and ordinary accents. Record red/green checks.
- [x] Reproduce the gate test's dependency on old `out/`; give the test its own manifest/report without weakening production diagnostics.
- [x] Observe current matrix rows in Word before and after save/close/reopen on a QA copy; keep Writer findings separate.
- [x] Ship a separate `scripts/transpect/prepare_libreoffice_mathml.py` command for the demonstrated W/L/T adapter, with new CLI tests in `tests/test_prepare_libreoffice_mathml.py`. Input/output are distinct; source and existing destination files are never overwritten. Emit JSON status, changes, untested conditions and an explicit application-review requirement. Empty/metadata-only/namespace-free input produces no candidate. Keep F expansion experimental; do not apply the adapter to normalized MathML/Word.
- [x] Check new adapter against the preserved probe inputs and recorded renders; inspect representative regenerated Math/ODT render if adapter output differs. All outputs remain needs_review, and known DOCX failures remain open.
- [x] Run Java/Python/workflow/modern gates, generate a new 32-file patch snapshot, compare package parts against the last verified snapshot and consolidate current docs/evidence.

Ruling: this is the already requested LibreOffice Math input route, using the bounded W/L/T design from the reviewed handoff. F, StarMath generation, whole-document ODT conversion and OLE safety expansion are excluded because their fidelity is not established. The CLI reports preparation, never application acceptance.
