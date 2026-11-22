# Review: shared Word/Writer spacing experiment and the two Word growth edits (2026-11-09, read-only)

**Verdict:** I found no P1 problems and no real errors in the builder or verifiers. Rejecting shared constants is correct. One P2 is about interpretation: the Writer source panels are not a faithful reference, so Writer-calibrated values such as 191/103 copy a Writer rendering artifact. Status stays needs_review, accepted 0, FULL_END_ONLY unsupported, existing skips unchanged.

## P2: Writer's source reference is distorted
- **What I saw.** On `writer-render-v2/spacing-matrix-v2/page-1.png`, the M1_SOURCE panel draws the OLE previews above the text baseline.
  - `(u_n)` and `u₄ =- 12…` ride high in the stem line.
  - In the answer row, "A." "B." sit visibly lower than their `u₁ =- 21…` images.
  - On `word-v2-spacing-page-1.png`, Word draws the same source OLEs on the baseline.
- **The numbers agree.**
  - Source label-to-stem is 21.568pt in Writer but 14.369pt in Word. Source stem-to-choice is 21.5 vs 19.44.
  - The native panels differ only by about 0.5pt and 2.2pt between the two apps.
  - So most of Writer's heading deficit (9.55 vs Word's 2.88) comes from Writer making the source line taller, not from the native output.
- **What follows.**
  - The Writer "exact" 0.00/0.00 at 191/103 (`comparison-v2.json:153-160`) matches Writer's mis-rendered OLE, not the authored layout.
  - The same applies at the top of a page: Writer's source starts at 36.858pt vs native 27.308pt, and Word's at 30.108pt vs 27.228pt.
  - `codex_dsmt4_shared_spacing_2026-11-09.md:30,32` should say that the Writer source panels show OLE baseline misplacement. Writer residuals should not be treated as fidelity targets.

## Claims that hold up
- **The labels bind correctly.** `compare_measurements_v2.py:11-17,22` keys each panel to its unique marker, requires a stem and a choice per panel, resets on `END_`, and requires all 16 panels. `:27-28` requires exactly one top label, one stem and one choice per page. `:40` re-checks the DOCX hashes after Word.
- **The builder is sound.** It verifies that relationships point at byte-identical parts (`build_matrix_v2.py:17-22`). It requires `lineRule=auto` (`:41`). It asserts that shape and object IDs are unique (`:68-69`). The v2 verification reports 84 + 21 native maths with unchanged trees.
- **Collapse behaviour (AFTER6).** In both apps, B178/B191 give the same label-to-stem value under AFTER0 and AFTER6, while source and native gain +6pt. So in these files the space between paragraphs behaves like max(previous after, next before). "Masks 6pt" (`report:30`) is accurate. This depends on the document's compatibility settings, so state that.
- **contextualSpacing.** The compensation is fully suppressed in both apps (`comparison-v2.json:186-208, 441-464`). That only happens because the label shares the question's paragraph style (`build_matrix_v2.py:43-45`). Real preceding paragraphs may not.
- **Page top.** The confound of source on page 1 versus native after `pageBreakBefore` is negligible here. The source-minus-native difference at the page top (9.55 / 2.88) equals the deficit measured mid-page in each app. So the claim that before-spacing is ignored after `pageBreakBefore` holds. Automatic page breaks are untested, as the report says.

## P3
1. **Word's measurements move in steps of about 0.24pt.**
   - Contextual B178 choice gap is 13.92 against native 14.16, though spacing should be fully suppressed (`comparison-v2.json:349`).
   - The B191 choice gap is 19.20 in the matrix but 18.96 at the page top (`:292` vs `:513`).
   - Treat Word residuals of 0.24pt or less as noise, including the "−0.24" for B191.
2. **The STYLE panels test only a simple case.** `build_matrix_v2.py:46-52` replaces the paragraph's original style with a one-level style that holds the whole spacing element. The results match AFTER0, so nothing broke. But this does not test partial inheritance, where the style supplies `before` and the paragraph sets other spacing attributes. A converter that writes direct `w:spacing` would hit that case. Don't let "style-provided ≈ direct" (`report:30`) stand for that.
3. **Unreviewed extraction step.** The `measurements.json` extractors (Writer/Word) are outside this review. Which y coordinate `r['y']` holds is taken from the report.
4. **Growth edits.** The two Word edits are consistent: +1 inside the delimiter, prose unchanged, box 1/0 kept. The 30 non-target math-text deltas (`growth-verification.json:10-41`) are exactly the occurrences of the earlier known Word normalizations (minus, prime, ℝ). The boxed case has 7 terms, so it does not exercise the overflow failure. The report says so.

## Smallest next layout direction
1. **Use Word's rendering of the source OLE as the reference.**
   - Word lays the OLEs out as authored; Writer misplaces their baseline.
   - Report Writer residuals as a secondary, cross-app impact measure, not a target.
2. **The answer gap is the one candidate value that already works in both apps.**
   - The deficits are 5.15pt in Writer and 5.28pt in Word.
   - 103 twips leaves 0.00 in Writer and −0.24 in Word, which is within Word's noise.
3. **The heading deficit against the Word reference is only 2.88pt.**
4. **Smallest experiment.** Add one panel per context with **58/103 twips** to the existing v2 matrix (58 twips = 2.88pt). Render it in both apps and record:
   - the Word residual against the Word source;
   - the Writer residual against both the Word-source position and Writer's own native position.

   Nothing else changes.
5. **Hold conditions.** contextualSpacing and page-top suppression still defeat any before-spacing. Any later rule must skip such paragraphs or show that the residual left is acceptable. It must not remove contextualSpacing or page breaks. No converter change until that is decided.
