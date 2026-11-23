# Remaining Claude review: resolution and one blocked confirmation — 2026-11-07

The previously outstanding review was dispatched to the same Claude Code session, read-only. It completed and reported **no new P1/P2**. Original review is preserved at `docs/working/dsmt4-history/claude_dsmt4_review_debt_2026-11-07.md` and `work/dsmt4-review-debt-2026-11-07/result.json`.

## Independently reviewed and closed

- Both layout P2 findings: cumulative displacement is no longer counted as independent local errors; absolute positions after unmatched page transitions are explicitly marked confounded.
- Heading binding, inline-reference exclusion, unique PDF selection and recorded line-box limits.
- Math content evidence for all7 arrow/integral cases. Claude read the initial and reopened PNGs directly and confirmed glyphs, labels, integrands and upper/lower bounds.
- Both vector render examples; the additional V rejection/presentation-preservation tests and importer-report field.
- Java multi-object color/size preservation and spaced-operator rejection tests.
- QA-artifact exclusion from candidate inventories.

These are scoped review conclusions. They do not certify the whole branch, interactive UI not independently observed by Claude, full Word/Writer layout or all265 source formulas. Existing needs_review/accepted0 and support limits remain.

## New P3: reproducible coverage measurement

Claude correctly noted that the earlier terminal-only calculation of `height-floor/measurement-v2.json` was not saved as a script.

Codex added `work/dsmt4-layout-investigation-2026-11-07/reproduce_height_measurement.py`. It recalculates anchors, inventory and coverage from the recorded DOCX/PDF inputs, asserts the **entire resulting report** equals the original reference, then adds hashes of inputs, measurement code and itself. It refuses to overwrite existing evidence.

Executed successfully:
`python3 work/dsmt4-layout-investigation-2026-11-07/reproduce_height_measurement.py`

Output `height-floor/measurement-v2-reproduced.json` matches the reference, including40 OLE paragraphs,40 changed,5 display and0 unmodified. Codex also independently recomputed all104 comparable local-gap deltas and verified the134/8/104/30 totals and same-page eligibility. This check is stored in `codex-independent-check.json` in the review-debt folder. No source, candidate or earlier evidence was overwritten.

**Independent Claude confirmation of the new script remains pending.** A separate, narrowly scoped followup to the same session returned: “You've hit your 5-hour limit · resets 12:10pm (Asia/Saigon)”. That failed invocation is preserved in `repro-result.json`; it is not credited as a completed review. No repeated retry, replacement agent or new automation was started.

## Current boundaries

Production code and tests did not change in this review-debt batch. Earlier118Java/144Python results remain historical checks; no fresh rerun is claimed. `git diff --check` passed. No commit/push/merge/PR edit. Writer DOCX arrows, full-exam reflow and wider source-semantic/UI acceptance remain open independently of this review debt.
