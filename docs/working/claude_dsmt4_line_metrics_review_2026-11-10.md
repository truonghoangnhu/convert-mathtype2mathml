# Review: DSMT4 line/formula height batch (2026-11-10, read-only)

**Verdict:** I found no P1, no P2, and no bugs that make the reported numbers wrong. The numbers I checked recompute, the mutation checks are complete, and the report's limitations are honest. There are three P3 provenance or interpretation items. Keeping everything in scratch is supported.

## Claims I verified independently
- **Mutation scope (`verify_scope.py:13-28`).** For each probe, the script removes exactly the expected changes, then requires the whole canonical document to match the base:
  - 85 shading elements or 85 left borders;
  - one `w:spacing` restored to its original attributes;
  - 4 `rSpRule` elements, each on a 3-row matrix with value 1.

  All other ZIP parts must be byte-identical. This supports "only the expected mutations".
- **Matrix selection (`build_matrix_gap_trial.py:9`).** Only matrices with exactly three direct rows are changed (4 of them), so the nested one-row matrix in option C is excluded. The report wording at lines 21–24 is accurate. It also correctly avoids calling the math trees byte-identical for this control.
- **Minimum-line control (`build_min_line_trial.py:9`).** ceil(57.36 × 20) = 1148 twips = 57.4pt. It is derived from the border measurement, which was itself validated against the unshaded source. It changes `w:spacing` only (`:13` asserts the math trees are unchanged).
- **Instrument distinguishability.** Shading and border colours step by 6/255 (`build_shaded_probes.py:17`), well above the 0.002 match tolerance (`measure_shading.py:31`). Each paragraph gets a distinct border colour, so Word cannot merge adjacent identical borders into one group.
- **Table arithmetic.**
  - Stem band totals: 21.12 + 20.88 = 42.00 (source) vs 27.60 (native).
  - Gap after the stem: 42.00 − 27.60 = 14.40.
  - Min-line: 37.44 + 19.92 = 57.36.
  - Ink shortfall after matrix gap: 50.52 − 47.40 = 3.12.
  - Ink values in `formula-ink-metrics.json` (with crop-edge flags all false): 50.52 / 35.88 / 35.76 / 47.40 (Word) and 49.80 / 44.88 / 44.88 / 44.88 (Writer).
- **Writer extraction (`extract_writer_metrics.py`).**
  - Paragraphs are matched by full normalised prose and order (`:19`).
  - A units guard checks page width (`:15`).
  - Geometry-validity flags are kept per frame and never filtered out (`:29`).
  - Line height and paragraph print height are stored as separate fields (`:25,29`).
  - The ink crops assert that every frame they use is valid (`render_math_crops.py:12`).

## P3 findings

**1. The source formula's ink height is measured on the border probe, but only text positions were validated.**
- `render_math_crops.py:8-9` measures the source formula on `Word-source-border.pdf`.
- `measure_border.py:7-8` shows that every PDF text word is identical to the unshaded control. In the source, though, the formula is an OLE image. Its placement and scaling are not text, so they were never compared.
- The risk is low: identical text implies identical line boxes. But the 50.52pt headline (report line 33) does not need the border PDF.
- Fix: run the same crop on `Word-source-control.pdf`, or compare the image placement transforms in the two PDFs. (Native OMML is text, so the native measurements are already covered.)

**2. The source column of the Word table has no generator script.**
- `compare_height_trials.py:6` computes allocations only for the three native cases. The source values (42.00 / 57.36 / errors 0) come from no script.
- I checked them by hand against `word-border-envelopes.json:134-166`: p10's last band ends at 234.48, which is p11's top; p11 ends at 291.84, which is p12's top. That gives 57.36, and the stem sum gives 42.00.
- Fix: compute these in the script as well.

**3. Table row 32 mixes two instruments.**
- The source value is a border stroke (`(biên)`, report line 32); the trial values are shading bands.
- In the source, the border bands tile the flow with no gaps. In the min-line trial, the shading band left a 19.92pt gap.
- So the two instruments may cover different parts of a line. Row 31 (allocation between adjacent bands) is the comparable one. Footnote row 32, or drop it.

Minor: `anchor_geometry.py:15` checks only the number of answer markers, not that each marker appears exactly once. The earlier `all_answers.py` was stricter. This has no effect on the reported results.

## Limitations already acknowledged (not bugs)
- Shading moves source text by up to 1.92pt, so it is rejected as a reference.
- Painted bands are not complete line advances, and neither is an internal line-box measurement.
- Writer's intrinsic line height is not its allocated print area (46.30 vs 57.40). The cached frame flags are marked with `*`.
- The direct CLI dump was rejected.
- The ink segmentation is specific to this one brace system. The Word crop region includes trailing punctuation; the Writer region follows the fly frame.
- Writer ignoring `rSpRule` was observed in this one control only.
- Pagination was not preserved (4 and 5 heading mismatches). Only page 1 of each trial was viewed. There was no UI edit/save/reopen.
- The input is a snapshot, not current converter output.

## Interpretation (supported, not overclaimed)
- The two controls separate row allocation from formula height. Min-line restores Word's row allocation (57.36) without changing the formula (35.76 ≈ 35.88). Matrix gap raises the formula (47.40) without restoring allocation (51.12) or the stem (−14.4).
- The report's decision not to adopt either change follows from this.
- One observation the report could add: the source OLE's declared height (55.15pt) is close to the source allocation (57.36). Its ink (50.52) sits about 4.6pt inside that box.
  - So the source row height appears to come mainly from the OLE frame, including MathType's padding, rather than from the formula ink.
  - This is consistent with the data, but not proven.

## One next bounded experiment (analysis only, no new DOCX)
Using `Word-source-control.pdf` and the existing VML-declared heights, measure **declared OLE height minus ink height** for the I-section answer OLEs.
- Use the same 600 dpi ink method with per-object crops.
- Optionally decode the matrix/line spacing values stored in the MathType equation data (MTEF) for I.2's OLE.

What the result decides:
- **The padding is roughly constant:** source row height is mostly frame padding. That points to row allocation (paragraph spacing) and not to changing the math.
- **The padding varies with content:** it points to spacing data stored in the MathType equation itself (MTEF) that the MathML/OMML conversion drops.

Neither result authorises a converter change on its own.

## What I inspected
- **Read in full:** the report; `compare_height_trials.py`, `render_math_crops.py`, `verify_scope.py`, `build_min_line_trial.py`, `build_matrix_gap_trial.py`, `anchor_geometry.py`, `build_border_probe.py`, `measure_border.py`, `measure_shading.py`, `build_shaded_probes.py`, `extract_writer_metrics.py`; `formula-ink-metrics.json`.
- **Searched only:** `word-border-envelopes.json`, for p10–p13.
- **Not read:** `LayoutDump.java`, `run_complete_layout.py`, `height-trial-results.json` beyond the matched lines, `writer-line-metrics.json`, `height-ledger.md`, and all images (including `comparison.png` and the context pages).

  So the Writer dump correctness, the 63/85 and 70/86 validity counts, the page and mismatch counts, and all visual claims are taken from the report, not checked.

Status unchanged: needs_review, accepted 0, scratch only.
