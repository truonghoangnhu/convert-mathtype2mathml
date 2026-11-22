# Follow-up review: post-review additions to the full-exam layout batch (2026-11-10, read-only)

**Verdict:** both P2 gaps from my previous review are resolved, and nothing is overclaimed. I found no new P1 or P2 problems, only three small P3 items. Status stays needs_review, accepted 0, scratch only.

## Resolved

**P2-1 — the question-to-first-answer gap is not paragraph spacing: resolved.**
- Report line 50 now says the question→A gap mixes stem line count, line pitch and height, the position of the "A" label next to a tall formula, and paragraph spacing. It also says adding `w:before` only aligns the chosen label.
- It does not take on my word "mostly": it explicitly says no quantitative breakdown exists yet. That is the right call.
- Line 52 and `diagnose_line_boxes.py:7,18-20` record the declared OLE heights separately from the PDF text-fragment heights.
  - I.2: declared answer OLEs 55.15pt vs text fragment 16.786735pt (`targeted-checks-post-review.json:34`).
  - No native formula height is inferred from the fragment; the native VML lists are empty, as expected for OMML.

**P2-2 — no heading→next-heading metric: resolved.**
- `summarize.py:35-57` adds whole-question pitch, never joins y values across pages, and uses one common set of intervals for source, baseline and trial alike (`:46,49`).
- It records the requested origins, the common origins, the common count, and per-stage counts (`:50-54`).
- The report's numbers match `question-pitch-metrics.json`:

| Set | Word MAE (pt) | Writer MAE (pt) | Common intervals |
|---|---|---|---|
| 11 starting intervals | 12.192 → 5.640 | 6.312 → 3.245 | 10 Word / 11 Writer |
| All 21 | 14.096 → 9.728 | 7.809 → 5.825 | 15 Word / 17 Writer |

- The common origins (Word 1–10, 13, 14, 15, 19, 21; Writer 1–10, 12, 13, 14, 15, 17, 18, 19) and the per-stage counts (Word 16/17, Writer 17/17) match report line 61.
- The report keeps every page split and calls this an in-sample fit, not a layout pass.

**Earlier P3s — resolved or documented.**
- The verifier now reads `trial-plan.json` and checks it against the app plan (`verify_artifacts.py:17-22`).
- The new guard against line-unit and autospacing spacing is in place (`build_app_trials.py:21-22`).
- The limits of the guards and of matching markers only in the PDF are spelled out in report line 63.

## New P3 items
1. **No run record for the grouping-control rebuild.**
   - Report line 65 says `build_grouping_control.py --output NEW_PATH` rebuilt the control byte-for-byte.
   - `targeted-checks-post-review.json:12-36` records only `all_answers.py`, `summarize.py`, `verify_artifacts.py` and `diagnose_line_boxes.py`; there is no entry for this script.
   - The script's own check (`:19-21`) is sound, but add its exit code and output path to the targeted-checks record.
2. **The new builder guard has never actually run.**
   - `build_app_trials.py:33` refuses to run when the output file exists, so lines 21–22 could not have been executed against the rendered profiles.
   - The outcome is not in doubt: `measurements.json` contains no `*Lines` or `*Autospacing` values, so the plan would be the same.
   - Still, describe it as a guard added afterwards, not one that took part in building these artifacts. Or give the builder an `--output` option, as the grouping script has.
3. **One constant remains in the verifier.** `verify_artifacts.py:21` still uses `{44:'230'}` to express the I.12 rollback relationship. It is now a cross-check rather than the source of truth, so this is acceptable. Taking it from the I.12 entry in `trial-plan.json` would remove the last hard-coded value.

## Not issues (already stated in the report)
- Pitch intervals can include section headers (line 54).
- Excluding pairs that cross pages takes the split cases out of the MAE; the splits are reported separately.
- The two MAE improvements are in-sample by-products, not out-of-sample validation.

## What I inspected
- **Read in full:** the appended section of the report (lines 46–67); `summarize.py`, `verify_artifacts.py`, `diagnose_line_boxes.py`, `build_grouping_control.py`; `targeted-checks-post-review.json`.
- **Searched only:** the guard lines in `build_app_trials.py`, and the cohort and MAE fields in `question-pitch-metrics.json`. I did not read the per-pair entries.
- **Not opened:** `line-object-diagnostics.json` beyond the printed I.2/I.6 values, the regenerated control file itself, and any images.
