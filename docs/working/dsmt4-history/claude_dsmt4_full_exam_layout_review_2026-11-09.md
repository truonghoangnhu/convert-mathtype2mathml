I've finished reading the scripts and checked three page renders; here is the review.

# Review: DSMT4 full-exam layout experiment (2026-11-09/10)

**Verdict:** I found no P1 problems and no bugs that make the reported numbers wrong. Every MAE value and ledger row I recomputed matches. There are two P2 interpretation and reporting gaps and four P3 reproducibility issues. Keeping everything in scratch is fully supported.

## Numbers I recomputed and confirmed
- **Mean absolute error of the heading→first-answer gap, same 11 intervals** (from `question-ledger.md`):
  - Word: 79.92 / 11 = 7.265 before, 14.64 / 11 = 1.331 after.
  - Writer: 49.05 / 11 = 4.459 before, 10.72 / 11 = 0.975 after.
- **New splits** in `summary-metrics.json`: ordinals 17/22 = III.1/III.6, 18 = III.2 and 21 = III.5. These match report lines 27–28.
- **III.1 split:** `Word-grouping-control-page-2.png` shows III.1's stem paragraph continuing onto page 3. The report's description is correct; the split happens inside the stem paragraph itself.
- **Trial plans:** `app-trial-plans.json` matches the report — 8 Word changes with I.12 rolled back, 9 Writer changes. The keepNext on paragraph 43 is declared as a new grouping property (`grouping-control.json:2-9`), not presented as preserved source formatting.

## P2 — interpretation and reporting gaps (not code bugs)

**1. The heading→first-answer gap mixes three effects, and the before-spacing fix treats them all as paragraph spacing.**
- Evidence:
  - Both builders compute the deficit as `heading_choice_gap_pt` (`build_trial.py:24-26`, `build_app_trials.py:22-24`). That value is the top of "Câu" to the top of "A." (`measure.py:52,67`).
  - In `Word-source-page-1.png` vs `Word-native-page-1.png`, I.2's "A." sits vertically centred on a 3-row system of equations. The source system is much taller than the native one.
  - The stems of I.2, I.5 and I.8 are two lines, and source line heights depend on the embedded equation objects (OLE).
- So the 18.96pt for I.2, and the 12.00pt for I.6, are mostly differences in line height and object height, not spacing between paragraphs.
- Adding `before` moves the "A." label to the reference position, but the bottom of the answer row and the next question still drift. Pagination depends on that drift.
- The report never says this. Its §1 "deficits vary" (line 19) and the MAE table (lines 24–26) read as if spacing were the quantity being fitted.

**2. The summary measures only the label position being fitted, not the spacing from one question to the next.**
- `measure.py:84-88` already computes `preceding_question_gap_delta_pt`, but `summarize.py:9-23` and the report table leave it out.
- The heading-to-next-heading distance is the quantity that causes the new page splits (III.1, III.6). Report it alongside the MAE, for the same 11 intervals and for all intervals that stay on one page.
- Without it, "7.265 → 1.331" can be read as a layout improvement. Its in-sample caveat (line 30) is correct, but it is not enough on its own.

## P3 — reproducibility and verifier
1. **`verify_artifacts.py:17-20` hardcodes the 9th change instead of checking it against `trial-plan.json`.**
   - It loads `trial-plan.json`, prints its keys, and never uses it.
   - The extra change `{44:'230'}` is a constant, so the verifier proves the DOCX matches the constant, not that it matches the recorded plan.
   - Fix: assert that `first['changed']` equals the expected change map.
2. **`build_app_trials.py:13-20` has no `afterAutospacing` guard; `build_trial.py:22` does.**
   - It has no effect here: there are zero `beforeLines`, `afterLines`, `*Autospacing` or `numPr` values in `measurements.json`.
   - But neither builder (and not `measure.py:15-30`) handles `beforeLines`/`afterLines` precedence, numbering pPr, or table-style pPr.
   - The guards fit this document only. Say so wherever the guards are described.
3. **Answer-marker binding (`all_answers.py:20-26`) matches individual PDF words, with no XML link.**
   - The exactly-one asserts catch ambiguity, but they cannot catch a real marker that is missing while a body word like "B." takes its place.
   - That is acceptable for a "location check" (report line 11). It means the 70 markers are bound in the PDF only, not to paragraphs.
4. **The first-word yMin is a top-of-font box.**
   - Each gap compares two first words in the same font and size ("Câu" and "A."/"a)"), so differences are close to baseline differences.
   - The "not baseline" caveat (line 13) is conservative and correct. Keep it; nothing needs fixing.

## Already acknowledged — model limits, not bugs
- Results are in-sample only, from one exam.
- The same before-values do not transfer between Word and Writer (I.6 +9.25pt, I.2 +7.27pt).
- keepNext is new grouping that changes position.
- The page-top check is heuristic.
- I.11 has no same-page reference.
- Writer's rendering of the source OLE is a diagnostic only.
- The native file is a snapshot, not a fresh converter output.
- No edit–save–reopen through the UI was done on these profiles.
- Pagination and equation content remain open.

## Is keeping everything in scratch supported?
Yes.
- The Word profile still splits I.12.
- Grouping fixes I.12 but newly splits III.1 and III.6.
- Writer's own profile still splits III.5.
- The same spacing values do not carry over between apps.
- The fitted lever (P2-1) is not the mechanism that drives pagination.

None of this supports a converter rule.

## One next bounded experiment (analysis only, no new renders)
Use the existing `Word-source.bbox.html` and `Word-native.bbox.html`. For all 22 questions, split each interval into four parts:
1. the number of stem lines and the pitch between them;
2. the gap from the bottom of the stem to the top of the answer row;
3. the offset of the answer marker within its line, which depends on the tallest inline object;
4. the distance from this heading to the next one.

If most of the deficit sits in line and object height (parts 1 and 3), paragraph spacing is the wrong lever. The next direction would then be line height or object metrics, not more `before`/keepNext tuning.

## What I inspected
- **Read in full:** the report; `measure.py`, `all_answers.py`, `summarize.py`, `verify_artifacts.py`, `build_trial.py`, `build_app_trials.py`; `grouping-control.json`, `question-ledger.md`, `summary-metrics.json`, `app-trial-plans.json`.
- **Searched only:** `measurements.json`, for the spacing attributes above.
- **Images viewed:** `Word-source-page-1`, `Word-native-page-1`, `Word-grouping-control-page-2`.
- **Not opened:**
  - the other source/native/grouping pages, the Writer profile pages and the Word-trial pages;
  - the render and evaluation scripts;
  - the full contents of `all-answer-bindings.json`, `trial-evaluation.json`, `app-trial-evaluation.json` and `artifact-verification.json`.

  So the III.5 Writer split and the Writer-side figures are taken from the ledger, not from images.

Status unchanged: needs_review, accepted 0, FULL_END_ONLY unsupported, skips and Lý ¶91 unchanged.
