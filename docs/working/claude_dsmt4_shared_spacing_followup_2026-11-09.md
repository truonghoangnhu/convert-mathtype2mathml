# Follow-up review: the v3 58/103 trial (2026-11-09, read-only)

**Verdict:** the P2 about the reference target is resolved. The v3 numbers check out. I found no real verifier errors, only one provenance gap. Before any full-context trial with compensation, I recommend a measurement-only full-context pass. Status stays needs_review, accepted 0, FULL_END_ONLY unsupported, skips and Lý ¶91 unchanged.

## P2 is resolved
- The resolution doc (lines 3 and 9) and `primary-Word-reference-v3.json:2` now:
  - label Writer-source residuals as renderer diagnostics;
  - pick Word's render of the source as the primary reference;
  - explicitly do not claim that Word was the authoring application.
- `comparison-v3.json` keeps the per-app diagnostics separate.

## Numbers checked against `comparison-v3.json`
All values in the resolution doc's table (lines 13–16) and the page-top paragraph (line 20) recompute correctly:

| Check | Calculation | Result |
|---|---|---|
| Word, AFTER0, B58 heading | 14.369 − 14.369 | 0.00 |
| Word, AFTER0, B58 choice gap | 18.96 − 19.44 | −0.48 |
| Writer B58 vs Word source, heading | 14.918 − 14.369 | +0.55 |
| Writer B58 vs Word source, choice gap | 21.5 − 19.44 | +2.06 |
| Writer B58 vs its native panel | — | +2.90 / +5.15 |
| AFTER6, Word | — | −2.88 |
| AFTER6, Writer vs Word source | — | −2.35 |
| Page top, Writer vs Word source | 30.108 − 27.308 | 2.80 |
| Page-top choice gaps | — | 18.96 (Word) / 21.5 (Writer) |

Other checks:
- `v3-verification.json` counts 112 = 16 native panels × 7 and 28 = 4 page-top cases × 7. Both are correct.
- `compare_measurements_v3.py:22,40` requires 20 panels and re-checks the DOCX hashes after Word.

## Verifier and provenance
1. **P3: one output has no generator.** No script writes `primary-Word-reference-v3.json`; the only match for that name is `claude-followup-prompt.txt`. The resolution doc calls this file authoritative (line 30). I recomputed its values from `comparison-v3.json` and they match, so this is a provenance gap, not an error. Add a small generator or put the derivation into `compare_measurements_v3.py`.
2. **The measurement code is now reviewed.** `render_matrix_v3.py:13-15` records the yMin of the first word on each matching line.
   - Every distance compares two first words of the same font and size ("M…" labels, bold "Câu", "A.").
   - pdftotext boxes come from font metrics, which I believe are not glyph ink. If so, these yMin differences approximately equal baseline differences.
   - So "text bounds, not baselines" is a conservative label. Keep it.
3. **Word's 0.24pt steps.** The same answer before-spacing of 103 twips gives 18.96pt for B58 and 19.20pt for B191 (in v2). The −0.48 choice-gap residual should be read as about two quantisation steps (0.24pt each), not as a measured offset.

## Existing data already explains the AFTER6 failure
- In both apps, the space between paragraphs behaved as max(previous after, next before), as established in v2.
- In Word:
  - AFTER0 with 58 twips gives 0.00 (v3).
  - AFTER6 with 178 twips gives 0.00 (`comparison-v2.json`, Word AFTER6 B178). 178 = 120 + 58.
- So under collapse, the compensation that matches is "before = effective preceding after + deficit", not a fixed value.
- This also explains the original 178 calibration in Word: that sample had an inherited 6pt after on the label.
- Writer keeps its +0.55 offset against the Word source in both cases.
- Collapse behaviour depends on the document's compatibility settings. Record the relevant `settings.xml` flags with any later trial.
- contextualSpacing and the page-top case stay outside this formula. They are suppressed, not collapsed.

## Recommended next step: measure first, without compensation
The 2.88pt and 5.28pt deficits come from one Câu 1 and its specific OLE heights. A full-context trial with compensation would apply 58/103 as if they were constants, but nothing yet shows they hold for other questions.

Smaller step:
1. In the real full-context Toán document, render source and native unchanged in Word.
2. For every question and its answer row, measure the heading and choice-gap deficits against Word's source render.
3. Record each question's preceding after spacing, contextualSpacing, style, and whether it starts a page.
4. Report Writer values only as a secondary diagnostic.

What to do with the result:
- **Deficits cluster near 2.88/5.28:** a context-aware compensation trial (preceding after + deficit; skip contextualSpacing; record page starts) is justified next.
- **Deficits vary with OLE height:** a fixed-value rule is ruled out. Any further direction would need a deficit for each paragraph, derived from the source OLE metrics. That is a larger design question for you to decide.

No acceptance tolerance, no production change, and no change to corpus status follows from v3.
