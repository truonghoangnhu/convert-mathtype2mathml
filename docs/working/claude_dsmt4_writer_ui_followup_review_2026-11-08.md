# Follow-up review: Writer UI round-trips and the boundary resolution (2026-11-08, read-only)

**Verdict:** the three Writer UI edit/save/close/reopen trials resolve only the Writer-authored part of the tall-growth confound (P2-2). Replacing the "box survives" check with recording the observed outer `m:box` 1→0 is correct. P2-1 and P2-3 are still open. Nothing is adopted into production. Status stays needs_review with accepted 0.

I found no P1 and no P2 errors in the new verifier or reports. There are a few P3 gaps and one wording mistake.

## What the new evidence supports
- **P2-2 is resolved for these three trials, and only for them.** `codex_dsmt4_writer_boundaries_2026-11-08.md:28-34` and `verify_ui_roundtrips.py:19-40` show the following for each file:
  - The edit was made in Writer at the calibrated paragraph (8, or 9 for page-edge).
  - Only math 1 changed text (`:29`).
  - The prose text is the same (`:28`).
  - The paragraph and answer identities are checked (`:34-38`).
  - The paragraph spacing is still 191/103 (`:39-40`).
- **The screenshots match the report.** I opened all four:
  - **tall-calibrated:** the full fraction is visible, with the A–D row below it.
  - **forced-wrap:** the six-term equation sits on its own line with the closing fence visible. "có" follows on the same line, and the rest of the sentence goes to the next line.
  - **page-edge:** Câu 1 is at the bottom of page 1 and the answers are at the top of page 2.
- **Box handling is right.** `verify_ui_roundtrips.py:41-47` records `outer_box_before`/`outer_box_after` without asserting them. `ui-roundtrip-verification.json:18-19,37-38,56-57` shows 1→0 in all three cases. The report says this plainly (`:40`) and nothing restores the box behind the UI's back.
- **Still not done:** numeric label measurements after the UI edits. The resolution doc admits this (`codex_dsmt4_writer_boundaries_review_resolution_2026-11-08.md:8`). So "fits" rests on screenshots only.

## Gaps in the new verifier and reports (P3)
1. **The box check only looks at math 1.** `verify_ui_roundtrips.py:46-47` counts `./m:box` on the edited equation alone.
   - So the evidence cannot tell apart "Writer rebuilds the edited object" from "Writer's DOCX export strips `m:box` from every equation".
   - The comment at `:41` ("Writer removes the original outer box during DOCX export") reads as the general claim. Only the narrower one is shown.
   - This matters for P2-3. If the export strips boxes everywhere, the `noBreak` protection is gone for the whole file after any Writer save. Word would then lay out those files differently from the converter's output.
   - Fix: count boxes on all 115 equations before and after. Apply the same count to the existing unedited `headless-roundtrip/*.docx` files.
2. **The "fits" evidence is visual only.** The cheap closure needs no UI:
   - Render the three UI-saved files headless and take `pdftotext -bbox` positions for the "Câu 1." and "A." lines.
   - Compare them with the injected probe (169.058/199.008) and the six-term probe (160.608/175.308/211.708).
3. **The page counts in the status bars disagree.** `tall-calibrated-ui-reopened.png` shows "Page 1 of 2" at 100% zoom. The forced-wrap and page-edge screenshots show "Page 1 of 4" at 130%.
   - Word and character counts are identical (1,815 / 7,928), so the most likely cause is that Writer had not finished laying out the document.
   - Don't cite these page counts. The headless render from item 2 confirms the real count.
4. **The edited files overwrote the originals, with no hashes kept.** The verifier reads `HERE/(name+'.docx')` (`:24`). Those are the same filenames `prepare_samples.py` created, and it refuses to run again (`assert not dest.exists()`).
   - Neither the manifest nor the verifier records a hash of the files before editing. Only hashes after editing exist (`:49`).
   - The comparison against `Toan-writer-before-sample.docx` still holds, so this is a provenance gap, not a correctness one.
5. **`'UI_edit_save_close_reopen': 'observed'` is hard-coded (`:48`).** It is a manual statement, not something the script checked. Label it that way, for example `"manual_observation"`.
6. **The crash's effect on the saved file is not recorded.** `:36` says the forced-wrap save crashed, recovery kicked in, and a retry succeeded. It doesn't say whether the retry started from the original file or from the recovered document. Record which; the XML checks still pass either way.
7. **`verify_growth.py` is stronger for Word only.**
   - The Word cases are now properly tied to the edited paragraph: `:24-29` (`len(ps)==3 and ps[1] is target_p`, then the identity checks, then 178/96).
   - The Writer cases still use fixed positions (`:53-55`, `ps[7]`/`ps[8]`) and never tie `writer-long` math 1 to its paragraph.
   - `:54` calls `.find(...).get(...)`. If the spacing element is missing, this crashes with AttributeError instead of failing an assertion.
   - The resolution's "P3-3 strengthened" (`resolution.md:10`) should say it applies to the Word cases.
8. **One stale word.** `codex_dsmt4_writer_boundaries_2026-11-08.md:53` still says "a substitute for the blocked interactive trials". Those trials are no longer blocked.

## Still open
- **P2-1:** no single spacing value has been checked in both Word and Writer. 191/103 and 178/96 are measurements from one sample each.
- **P2-3:** Word behavior on wrap, overflow, no-box and page-edge is untested; I understand that work is in progress separately.
  - Add the UI-saved Writer files to that comparison. Their math 1 no longer has the box, so they are the realistic case of "Word opening a file Writer has edited".
  - The Writer no-box A/B still says nothing about Word policy.
- **Other P3 gaps from the earlier review:** page-top spacing suppression, how symbols render going from Word back to Writer, effects of contextual, style or preceding spacing, and the run properties in the deterministic probes.
- **Scope I accept as written:** the nine-term overflow is a synthetic growth limitation, keepNext is rejected, and the page-edge split is normal pagination.

**Status:** needs_review, accepted 0, FULL_END_ONLY unsupported, original safety skips and Lý ¶91 unchanged. Nothing is ready for production.
