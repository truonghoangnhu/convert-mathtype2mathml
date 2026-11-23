# DSMT4 compatibility follow-up implementation plan

Goal: reduce verified Writer/Math content and placement failures while retaining Word behavior and safe unsupported boundaries.
Architecture: isolate probes first; only apply a measured, narrowly guarded converter/Math-adapter rule after red-to-green tests. Keep normalized MathML/Word and Math preparation scopes separate. Existing user-approved native execution continues; Claude reviews at the scheduled time.
Tech stack: Java/XML/XSLT, Python Math adapter, installed Word/LibreOffice, CUA UI.
Spec: docs/dsmt4_migration_acceptance.md and user migration/fidelity criteria.

Global constraints: root dirty checkout, no Git publication/reset/new worktree; no in/ZIP/fixture/old-output writes; FULL_END_ONLY unsupported, old safety skips and Lý¶91 retained; needs_review until content/editability/placement/display acceptance.

- [x] Writer arrows: reproduce labeled groupChr and saved structure; compare one change at a time against installed importer; inspect initial and reopened render. No change to normalized Word representation unless Word rendering/edit/reopen is demonstrated.
- [x] Math toan016: compare its single-cell table envelope with already tested flat A shape; prototype annotation retaining presentation; verify full row text and left alignment in initial/reopened render; add boundary regression before any production change.
- [x] Integration: fresh appropriate tests, versioned outputs and exact delta/preservation audit; ledger binds new artifacts and separates route/UI scopes; no acceptance from counts.
- [ ] Final review: prepare concrete handoff for exactly one real Claude Code session at 01:35 Nov7; resolve findings safely, report remaining limits and tested/not-run scopes.

Review focus: annotations override presentation; foreign/mixed content must not be rewritten; nested styling/table attributes must not disappear; groupChr labels vs arrow sizes are distinct; initial render does not prove saved/reopened fidelity.
