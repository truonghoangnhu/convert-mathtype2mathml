# Claude read-only inline-boundary review — 2026-11-06

Session c1780205-5a4b-4ce5-8fc0-84fcdd5c8f6e. Snapshot before the review fixes; no code/test/UI execution by Claude.

I found one real bug and one fail-open gap inside the scope you defined. Telemetry has one gap, and the tests miss some cases. No full DSMT4 acceptance claim is made here.

## Findings

**1. Medium (bug): the multi-object path misses a letter in the same run as the object**
- `InlineBoundarySafety.java:16` only starts looking at `run.getNextSibling()`. It never looks at what comes after the `<w:object>` inside its own run.
- The single-object path is safe: `InlineSafetyEvaluator.java:61-82` rejects any non-object child in the run before the boundary check at line 90.
- The multi-object path accepts mixed runs and splits them (`XmlBeansOmmlInjector.java:330-360`; test `splitsMixedObjectRunAroundEquationInMultiObjectParagraph`, line 456).
- Example: `<w:r><w:object>p</w:object><w:t>khối</w:t></w:r> … <w:r><w:object>V</w:object></w:r>`.
  - The check returns false and the paragraph is patched to `math'p'`, `r[t'khối']`.
  - The gap that the OLE viewport supplied is silently lost. This is the exact li002 case you're guarding against.
- Fix: scan the object's following siblings inside its run first, using the same rules, then continue to the next runs.
- Add a test using `mixedObjectRunXml` with the trailing text changed to a letter.

**2. Low (fail-open gap inside your scope): `w:lastRenderedPageBreak` stops the check**
- `InlineBoundarySafety.java:23`: if the following run is `<w:r><w:lastRenderedPageBreak/><w:t>theo</w:t></w:r>`, the check returns false and the object is patched.
- Word writes this marker at the start of whichever run began a page on its last layout. Converting to OMML changes widths, so that boundary can move to mid-line.
- It draws nothing, just like bookmarks and `proofErr`, and the codebase already treats it as harmless elsewhere (`patchesMultiObjectParagraphWithBenignLastRenderedPageBreak`). It should be skipped over the same way.

**3. Low (telemetry): the smoke script doesn't know the new reason**
- `scripts/workflow/run_docx_patch_smoke.py:44-57`: `SKIP_REASON_ORDER` doesn't include `INLINE_SPACING_REQUIRES_REVIEW`.
- So it's left out of both `STRUCTURAL_PATCH_SKIP_REASONS` and `NON_PATCH_CANDIDATE_SKIP_REASONS`, and `equation_structural_residual_skips` (line 832) undercounts.
- It still appears in the printed breakdown, but only as an extra sorted after the known reasons (`merged_keys`).
- The unit is also inconsistent: the single path counts per object, the multi path per paragraph. A spacing-retained paragraph with three objects adds 1. This follows the existing convention, but the docs should say so.

**4. Test gaps (no defect found behind them)**
- `retainsWholeMultiObjectParagraphAtUnseparatedWordBoundary` (line 1580) checks `multiObjectSkippedUnsafeParagraphs == 1`. Any UNSAFE reason satisfies that, so it should also check `skipBreakdownCount(INLINE_SPACING_REQUIRES_REVIEW) == 1`.
- Priority is only tested for a conversion failure on the single path (line 1609). Nothing tests unresolved manifest (single or multi), native OMML, or duplicate/unmapped relationship ids when an unseparated boundary is also present.
- The priority order itself is correct in the code:
  - `DocxMathPatchMain.java:201-210`: native short-circuits, then resolution runs before the spacing switch.
  - `DocxMathPatchMain.java:245-272`: native, unknown and unresolved are checked before the evaluator.
  - `MultiObjectSafetyEvaluator.java:27-102`: run before line 103.
- There is no test for finding #1.

## Checked and fine
- **No changes on a hit:** both skips happen before the inject step, and the tests compare the output XML exactly to the source.
- **Whole-paragraph retention:** in a multi-object paragraph, a hit on any object returns before any change is made (line 103).
- **Block candidates** skip the check, but by definition they are the only content in their paragraph.
- **Objects in runs nested in `w:hyperlink`/`w:ins`/`w:smartTag`:** the check returns false at line 15, but `isRunOf` (`XmlBeansOmmlInjector.java:86,153`) rejects those runs, so the original is kept (reported as XML_MUTATION_ROLLBACK, not spacing).
- **No guessing from content:** the check never reads the preview, fingerprint or formula content.

## Deliberately out of scope (not defects)
- A letter right before the object (`khốip`).
- Digits right after it.
- A following wrapper element (`w:hyperlink`/`w:ins`/`w:sdt`/`w:fldSimple`) that contains a word starting with a letter: line 19 ends the check, so the object is patched.
- Zero-width or soft-hyphen first characters.
- A leading space in a `w:t` without `xml:space="preserve"` (Word may collapse it, but this check counts it as a separator).

## Limitations
I only read the code; nothing was compiled or run. I didn't look at li002/li010 or at how Word lays out the patched output. I also didn't check what POI's `getRuns()` includes beyond what the injector's `isRunOf` guard covers.
