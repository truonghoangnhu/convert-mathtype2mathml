# Claude closeout review and Codex resolution — 2026-11-07

Claude review ran after01:35 in the existing session and completed without a credit block. The original result is preserved in `work/dsmt4-acceptance-closeout-2026-11-07/claude-review-result.json` and `docs/working/claude_dsmt4_closeout_review_2026-11-07.md`. Claude used read-only tools and did not run tests, rendering or UI.

## Findings and resolution

- **Code:** Claude found no P1 or P2 in the leading-temperature helper or bounded Math V parser. This is code review, not application acceptance.
- **One P2 evidence gap:** hoa037/042/066/067/086 and toan053/054 lacked current content-level evidence for arrows, labels and integral limits. Codex freshly rendered all7 prepared candidates, saved ODT, reopened and rendered again. Both complete pages were viewed; the initial/reopened PNGs are pixel-identical. Reopened PDF text contains exactly **1 ⇌, 5 → and 2 ∫**; saved commands retain each case's expected labels/terms and both integrals' upper2/lower0 bounds. Per-case checks are in `claude-followup/seven-content-review.json`. This closes that evidence gap for isolated Math candidates; no new full-layout or UI acceptance is claimed.
- **P3 V tests:** added root display attribute, styled identifier/operator, extra mover attributes, positive/doubled signs, two-coordinate tuples, separators, NBSP and mstyle rejection cases. Added an already-prepared positive case asserting the complete presentation tree stays identical inside semantics.
- **P3 Java tests:** added color/size preservation inside the temperature delimiter on the multi-object path, and direct OMML with spaced operator text (` > `), which must not trigger grouping.
- **P3 report:** V now records `annotation_priority_measured_on`. Metadata input continues to be preserved byte-for-byte; its conservative diagnostic wording is unchanged.
- **P3 QA artifact:** `vectors-ui-edited.odt` is explicitly excluded from candidate inventories, which enumerate `mathml/*.mathml` only. Existing evidence is kept at its referenced path; no file was moved or overwritten.

## Verification after review

Fresh tests: **118 Java, 0 failures/errors; 144 Python, all passing**. `git diff --check` passed. Regenerating candidate strings from all265 source sidecars reproduces all265 current MathML output bytes exactly; the post-review source change affects report metadata only, not formula serialization. No new package/corpus/gate run is credited, since Java production code and generated formula bytes are unchanged. The earlier116Java/gate4/4 and corpus audit remain historical evidence for their recorded snapshot.

The revised current occurrence ledger is `work/dsmt4-acceptance-closeout-2026-11-07/claude-followup/current-ledger.json`, with7 additional scoped Math content checks. All265 identities, prior route distinctions and **accepted0** remain. Current full failed total is still not established.

## Remaining support limits

Writer DOCX labeled-arrow fidelity and full-exam reflow remain open. Native/retained-object preservation does not certify rendering metrics. Broader interactive editing coverage and full source-semantic/layout acceptance have not been completed. FULL_END_ONLY remains unsupported and old safety skips/Lý paragraph91 stay retained. No commit, push, merge or PR-state change was made.

The requested one-time Claude review and its Codex followup are complete. The schedule is stopped; this does not mark overall DSMT4 migration acceptance complete.
