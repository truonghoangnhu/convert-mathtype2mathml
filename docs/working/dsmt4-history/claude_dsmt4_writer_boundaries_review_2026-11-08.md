# Review: DSMT4 boundary experiments and growth/cross-app evidence, 2026-11-08 (read-only)

Status stays **needs_review**, **accepted 0**. FULL_END_ONLY stays unsupported. The original safety skips and Lý ¶91 are unchanged. Nothing here is production-ready. No P1 was found this round.

## Accepted correction
I accept withdrawing the "math78 plain R lost" finding. `writer-long-word-double-struck-R.png` shows Word displaying `(a ∈ ℝ)` correctly. The same screenshot also shows `P′(t)`, `G′(t)`, `h′=30cm` and the minus signs in `M(−779; −260; 8)` rendered as prime and minus in Word. So within Word at that zoom, the minus/prime/ℝ changes in `review-evidence-corrected-2026-11-08.json:9-158` are normalizations, not failures. The remaining risk is in the other direction (see P3-4).

---

## Observed failures

**F1 — The nine-term equation is clipped in Writer, and saving does not fix it.**
- Evidence: `codex_dsmt4_writer_boundaries_2026-11-08.md:15,38`, `headless-roundtrip/summary.json:27` (`last_overflow_term_in_PDF_text: false`). I opened `pre-ui-diagnostics/overflow/page-1.png`: the equation sits on its own line, runs to the edge of the page, and is cut after `+2012345667`. The last term and the closing fence are missing.
- What this is: a Writer limitation that shows up after a user edits an equation (an OMML formula becomes one object that cannot break). Nothing shows it is a conversion defect. The source MathType OLE object could not wrap either. The case is synthetic (`render_diagnostics.py:31-37`).
- The no-box A/B (`:22`) only rules out removing the box as a fix **in Writer**. It must not be applied to Word.

**F2 — Near the bottom of the page, the question stays on page 1 and its answers move to page 2.**
- Evidence: `:16,18,39`. This is ordinary pagination: the line grew by about 8pt (721.058 → 729.058). It is not a converter defect.
- keepNext (`:24`) changes layout away from the source, so it must not become policy. The document already says so correctly.

---

## P2 — Gaps that must be closed before any converter change

**P2-1 — No single spacing value is known to work in both apps.**
- Writer is calibrated at 191/103 and Word at 178/96, each on its own sample (`codex_dsmt4_layout_spikes_2026-11-07.md:25-33`). The converter can write only one value into the DOCX.
- Not yet run: Word rendering the Writer-calibrated sample, and Writer rendering the Word-calibrated sample.
- Until you have the residual of one chosen value in both apps, the spacing-before direction is only per-app calibration on a single sample.

**P2-2 — The tall-calibrated probe is confounded.**
- `render_diagnostics.py:19,28-29` replaces the **whole** first oMath with the oMath Word saved in `word-tall.docx`. That brings in Word run properties and default 11pt runs (growth doc `:14`).
- It also does not establish whether the production `m:box` structure survives. It is a replacement, not an edit authored in Writer.
- `boundaries.md:13` ("Local content fits") should say: a Word-serialized replacement fits; a tall edit authored in Writer at paragraph 8 is not run.
- The only UI tall edit in Writer is at math14 (Câu 2 B), outside the calibrated area.

**P2-3 — Word's behavior on wrap, overflow and the page edge is untested.**
- The production `m:box`/`m:noBreak` stops Word from breaking an inline equation at operators. Without the box, Word normally can break there.
- So the effect of the box in Word on six terms, nine terms and the edge case is unknown. Every current conclusion comes from Writer only.

---

## P3 — Measurement and evidence flaws

1. **The spacer changes the context the calibration depends on.**
   - `prepare_samples.py:25-30` inserts an empty spacer (exact 560pt, after=0) right before paragraph 8. The 191 value was calibrated against the original preceding paragraph; Word's 178 even includes a 6pt after spacing inherited from the label.
   - So the edge probe does not check calibration at the page boundary. It only checks pagination.
2. **The page-top measurement is unread.** keepNext puts Câu 1 at yMin 35.306pt on page 2 (`:24`). In the split case, answer A is at 26.858pt (`:18`).
   - These are text boxes on lines of different heights (one has a fraction), so they cannot be compared.
   - No one has checked whether the 191 twips before Câu 1 is applied or suppressed at the top of a page.
   - The data is already there; you only need the top margin to read it.
3. **`verify_growth.py:23-24` does not bind the edit to the calibrated paragraph.** `before[-2:]==["178","96"]` does not check which paragraph holds the edited oMath.
   - `word-tall-reopened.png` shows the Word sample is a short document with only Câu 1 plus the A–D row, so this is a minor issue. It should still be asserted by index.
   - There is also no builder script for the Word 178/96 sample or for `word-before-comparison.docx`, so its provenance is not reproducible.
4. **The reverse cross-app direction is unchecked.**
   - `verify_growth.py` checks math78 only for `writer-*` cases. Word→Writer has no ℝ check.
   - No one has looked at how Writer renders the ASCII `-` and `'` that Word writes (occurrences 77/83/89 and the minus signs). Word displays them correctly; Writer is unknown.
5. **`headless_roundtrip.py:43-44` compares only the first math.** The other 114 equations are only counted (`:42`).
   - That is fine for a targeted probe, but not for a whole-document claim.
   - `first_page_pixels_same: false` in all 4 cases. The report (`:41`) correctly makes no pixel claim.
6. **`render_diagnostics.py:32,35-36` copies only `w:rPr`, not `m:rPr`, into the new runs.** This barely matters for the numeric terms, but it is a further difference from what a UI edit produces.
7. **Some statements are stale.** "Claude review blocked/no result" appears at `codex_dsmt4_writer_boundaries_2026-11-08.md:45`, `codex_dsmt4_growth_roundtrip_2026-11-08.md:44` and `review-evidence-corrected-2026-11-08.json:163`. Replace these with a pointer to this report.
8. **Text bounds are not baselines.** Every yMin cited is a pdftotext text box. Comparisons between lines of different heights (fraction vs. no fraction) only support conclusions about order, not exact offsets.

---

## Not run (do not count as done)
- All 3 interactive Writer cases (tall-calibrated, forced-wrap, page-edge). The Mac lock blocked them; headless runs do not replace them.
- Word rendering of wrap, overflow, overflow-no-box and edge-tall.
- Cross-app residuals of the spacing constants (P2-1).
- The spacing guards: contextualSpacing, page top, preceding after-spacing, spacing inherited from a style, multi-line paragraphs.
- A visual check in Writer of the ASCII minus/apostrophe written by Word.

---

## Smallest next experiments

**(1) Tall growth authored in Writer at the calibrated paragraph.**
- Steps: open `tall-calibrated.docx` in Writer. Confirm the Commands content of Object 1 before editing. Add a fraction inside the fence. Save as DOCX, quit, reopen.
- Assert:
  - exactly one oMath changed, at index 0;
  - paragraphs 7 and 8 still have before = 191/103;
  - the outer `m:box` is still there.
- Measure "Câu 1." and "A." against the untouched render and against the injected probe (169.058/199.008).
- If the Mac is still locked, keep it **not_run**. Do not substitute headless.

**(2) Wrap and page boundary in Word, opening only with no edits.**
- Open the existing `pre-ui-diagnostics/{wrap,overflow,overflow-no-box,edge-tall}.docx` in Word and export to PDF or take a screenshot.
- Record:
  - with and without the box, does the equation move as a whole or break at operators?
  - is the nine-term equation clipped or does it break?
  - where does the edge-case page split fall?
- Add no keepNext. This answers P2-3 and decides whether the box is a problem on the Word side.

**(3) A spacing guard matrix with one variable at a time.**
- From `Toan-writer-before-sample.docx`, build 4 variants:
  - (a) contextualSpacing on paragraphs 7 and 8;
  - (b) Câu 1 pushed to the top of a page with `pageBreakBefore` (not keepNext);
  - (c) the preceding paragraph's after spacing at 6pt vs 0;
  - (d) spacing set by style instead of directly on the paragraph.
- Run each in Writer headless and in Word, measuring only the label yMin values against the source.
- Fold in the P2-1 cross-check: render the 191/103 sample in Word and the 178/96 sample in Writer.

---

## Guards required before any converter change
- Do not remove `m:box` and do not add keepNext or frames based on Writer results.
- Write `before` only when there is no existing value or it is 0, `lineRule=auto`, and the spacing is direct, not from a style (as already asserted in `spacing_before_probe.py`). Never overwrite spacing that comes from a style.
- Do not use 191/103 or 178/96 as general constants. They are specific to this sample, and a general rule needs (3) plus P2-1.
- Keep the source's page-top behavior. Measure it with (3b) first.
- Treat overflow as a limitation that appears after user edits and record it separately. Do not "fix" it in the converter unless real source equations are shown to come close to the page width.

**Verdict:** two failures are observed on synthetic inputs: clipping in Writer, and pagination when growth happens near the bottom of the page. Neither is a converter defect. The prototype's evidence is not enough for any converter change; P2-1 through P2-3 and the three experiments above are still open.
