# DSMT4 real-wrap spike: final evidence delta review (2026-11-12)

**Scope:** I reviewed only the final delta, read-only. Sources: report lines 31-55, `reopen-followup.json`, `saved-structure-check.json`, `verify_saved.py`, `checkpoint.json`, `review-v2/probe_controls.py` and `review-v2/results.json`, plus a directory listing.

I did not open any PDF or contact-sheet image from this delta. The pixel observations below come from Codex, and I do not certify them independently.

**Verdict:**
- No P1 issues.
- **The Writer UI gap is closed.** Writer has now been reopened through the UI and a PDF exported (report line 51; `reopen-followup.json:3-8`; `saved-structure-check.json:23`).
- **The INT content failure is still recorded explicitly** (`saved-structure-check.json:27-33`; `checkpoint.json:2,15`).
- **Nothing was promoted:** accepted is 0, with no production change, commit or push (`reopen-followup.json:15-16`; `checkpoint.json:13-14`).
- **Two new P2 reporting gaps:**
  - the new raw-delta data shows Word rewrote every minus sign, and the report does not say so;
  - the probe record for the unboxed control measures the wrong formula.

## Prior findings: status

| Prior finding | Status |
|---|---|
| P2-1: empty-group and trailing-equals out of date; trailing-equals had no generator | **Closed.** Both variants are rejected with reasons (report lines 33-35; `checkpoint.json:17-20`). The generator and input SHA are now in `probe_controls.py:9,16,31`, and the result shows 2 rows (`results.json:47-57`). |
| P2-2: `m:nor` variant possibly malformed | **Closed.** A single `m:rPr` is now placed first and asserted (`probe_controls.py:17-23`). The = is still lost (`results.json:17-31`). No full-DOCX schema validation was run; report line 41 says so. |
| P2-3: control with the box removed and no eqArr was missing | **Closed for this decision, with caveats** (P2-2 and P3-3 below). The Word UI render was done as render-only (report line 53). |
| P3 verifier items | **Addressed.** Raw minus deltas are now recorded, the ROOT path is fixed, the final UI SHA is recorded, and 6 oMath plus the row count are asserted (`verify_saved.py:5,17,20,22`; `probe_controls.py:30`). |

## New findings

**P1:** none.

**P2-1 (reporting, substantive) — Word's save replaced every U+2212 minus with an ASCII hyphen-minus "-", and the report does not say so.**
- The new raw-delta data (`saved-structure-check.json:35-71`) shows this in **all six Word formulas**. That includes the baselines nobody edited and the CHEM charge "HSO₄−".
- Writer kept U+2212 everywhere; its only delta is the INT = (lines 72-77).
- Report line 45 says only that the delta "is now recorded". Meanwhile `only_expected_math_text_edit_modulo_minus: true` for Word (line 10) reads as "no unexpected change".
- Word may still draw the hyphen as a minus inside math, but I am not certifying that. Either way, the stored content changed, which matters to any later step that reads the XML or opens a Word-saved file in Writer.
- **Fix:** state it in the report and in `checkpoint.json`, as Word's save behaviour rather than a converter defect.

**P2-2 (evidence record) — The `unboxed-no-array` row in `results.json` does not measure the unboxed control.**
- `probe_controls.py:11-13` removes the box only from formulas 0, 2 and 4, the baselines.
- Lines 30-31 still report on `ms[3]`, the INT explicit formula, which this mode leaves untouched. So `results.json:33-46` (`second_equals_present: false`, `full_text_match: false`) says nothing about the control. It can be misread as "the unboxed control loses =".
- Nothing checks that removing the box preserves the formula text or its order. `m.extend(list(e))` appends the box contents at the end and would silently reorder anything else in the oMath.
- As a result, both the Word claim ("auto-wraps") and the Writer claim ("still clips") about this control rest only on viewing the renders.
- **Fix:** for this mode, assert that the text of formulas 0, 2 and 4 is equal before and after, and report those formulas.

**P3-1 — Point-in-time hashes while Word may still have files open.**
- `~$rd-real-wrap-ui.docx` and `review-v2/~$boxed-no-array.docx` are still in the folder. These are Word lock files, so Word may still have the UI file and the control open, or the locks are stale.
- `final_saved_sha256` (`saved-structure-check.json:14,24`) and `input_sha256_unchanged: true` (`reopen-followup.json:10`) are snapshots taken at one moment. The second records a boolean, not the hash value.
- **Fix:** close Word, re-hash, and record the actual post-UI SHA of the control.

**P3-2 — Some status fields are hardcoded or stale.**
- `verify_saved.py:20` hardcodes `actual_UI_reopen_done: True` for both apps. It is a human observation written into a script's output. Take it from `reopen-followup.json`, or rename it, e.g. `reopen_observed_by_codex`.
- `checkpoint.json:16` still says "investigate Commands afterunlock", although the Mac is unlocked.
- The report body still contains statements that have since been superseded: lines 19, 21-23 and 27 ("chưa reopen", "giữ đủ hai dấu ="). They are corrected only further down, at lines 31-35 and 51, and the summary at line 3 does not give the final status.
- **Fix:** add a short final-status banner at the top of the report.

**P3-3 — The Word unboxed claim should keep a narrow scope.** Line 53 ("không cần eqArr cho ba ca Word này") is correctly limited to these three cases, but:
- the control was only rendered, never edited, saved and reopened;
- the line-break positions and quality were not described, for example whether INT breaks before "=";
- it was tested only in the artificial 180pt column;
- removing the converter's no-break box is itself a change to converter output and needs its own policy.

## Remaining actual defects (product or application behaviour, not reporting)

1. **Writer drops the leading = at the start of INT explicit row 2 on DOCX save.**
   - Evidence: Writer Commands after reopen (Codex observation); the saved XML; and headless runs of the baseline, `nor`, schema-order `nor` and box variants.
   - Both workarounds are rejected: empty-group adds a stray ")", and trailing-equals merges rows.
   - The leading −, + and → survive.
   - When LibreOffice imported the original control, it displayed the = (seen in my earlier review). That points to export as the cause, but this is not proven.
2. **Writer does not wrap long single-line OMML.** The INT and CHEM baselines clip whether or not the box is present (headless render, and the UI PDF viewed by Codex).
3. **Inherited problems:**
   - INT's empty integral operand, which LibreOffice renders as □;
   - the plain "2e" in CHEM.
4. **Word's save normalizes − to "-"** (P2-1 above). Its impact further down the pipeline has not been assessed.

**What this means:** no single wrap form works in both applications for these cases.
- In Word, the unboxed form wraps on its own (render-only evidence).
- In Writer, the explicit eqArr works for EXP and CHEM but breaks the = in INT, and removing the box does not help.

## Next action

1. Investigate how Writer handles a row-leading relation in a stack.
   - Write the same three-row INT stack directly in Writer Commands, for example with `{} = …`. Save, close, reopen and export a PDF.
   - Compare the OMML Writer exports from that with the failing file.
   - Do not change production until a form that survives Writer's save exists, or until a policy explicitly scopes behaviour per application.
2. Housekeeping for the record:
   - close Word and re-hash the files;
   - fix the unboxed check in `probe_controls.py`;
   - disclose the minus normalization;
   - add the final-status banner to the report.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged.

**Not inspected:** the PDFs (`writer-real-reopened.pdf`, `word-unboxed-control.pdf`), `writer-ui-contact.png`, `word-unboxed-contact.png`, the trailing-rt-render images, the DOCX/ZIP XML itself, and the prior review document (not reread).
