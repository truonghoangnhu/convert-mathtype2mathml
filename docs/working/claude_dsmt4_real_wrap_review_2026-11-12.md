# DSMT4 real-formula wrap spike: review (2026-11-12, read-only)

**Scope:** I reviewed only the partial evidence for this spike, with Read/Glob/Grep. Nothing was edited, executed or committed.

**Verdict:** There are no P1 issues. The main problem (P2-1) is that the report is out of date. Its text about the empty delimiter group (lines 21-23) has been overtaken by the render and by Codex's own checkpoint: that variant renders a stray ")" and was rejected. A fifth variant, trailing-equals, appears in the batch files but not in the report.

The Word evidence supports the report's claims. The Writer evidence is incomplete: Writer edited and saved, but **reopen and PDF are NOT DONE** because the Mac locked. This review does not fill that gap.

## Confirmed statements

**Provenance**
- Each case is located by source paragraph index and OLE object ordinal. The script checks that the ProgID is `Equation.DSMT4` and that the OLE and oMath counts match (`build_real_probes.py:28`).
- `plan.json:20-79` records the hashes of the source file, the output snapshot and the OLE BIN, plus the relationship ID.
- `verify_saved.py:20-21` re-hashes the source files and snapshots.

**Explicit cuts**
- The cuts are written by hand for each case (`build_real_probes.py:33-39`); this is not an automatic rule. The rows in `plan.json:34-36, 54-56, 74-76` match the report (line 7):
  - EXP is cut before −5000 and before +200000;
  - INT is cut before the second = and before the last integral;
  - CHEM is cut before +3H and before →.

**Subtree preservation**
- The full `m:t` text sequence is equal before and after the cut (line 43).
- Every `sSup/sSub/nary/d/f` subtree has an identical signature: tag, attributes, text and children (lines 45-46).
- Only plain runs are split, via a deepcopy with the run properties kept (`run_text`, line 15-16).
- The candidates also drop the outer `m:box` wrapper together with its `boxPr` (line 32). The report says so (line 7).

**Word UI (EXP explicit only)**
- The edit was 200000→200001, followed by save, close and reopen. The other five formulas only went through the document round trip (report line 13; `plan.json:81`).
- What I saw in `word-ui-contact.png`, `word-ui-page-4.png` and `word-ui-page-6.png`:
  - all three candidates render as 3 rows, with the sentinel line below;
  - EXP's last row reads +200001;
  - the INT baseline runs off the page at "(2.", and the CHEM baseline at "2H₂O(l".
- The failed whole-equation replacement is kept as a separate file and was disclosed (report line 15; `ui-failed-attempt.json`).

**Writer**
- The edit was saved and the file closed. **Reopen and PDF are not done** (report lines 19, 27; `checkpoint.json:2,11`).
- In the XML, Writer's save keeps all six formulas and EXP reads 200001. However, row 2 of INT explicit has lost its leading = (`saved-structure-check.json:23-29`). INT had no interactive edit, so the document round trip alone causes this loss.

**Inherited limits (unchanged)**
- INT's first integral operand is empty. LibreOffice renders it as a visible □ placeholder; Word shows a blank gap (`control-render/contact.png` pages 3-4; `word-ui-page-4.png`).
- In CHEM, the electron is plain "2e".

**Scope**
- These are real formulas placed in an artificial 180pt column on a 400pt page (`build_real_probes.py:56`; `plan.json:2-4`). This is not full-exam fidelity.

**Leading = in headless Writer**
- The plain baseline, the `m:nor` variant and the whole-row `m:box` variant all lose the = (`leading-relation-results.json:2-19`).
- The empty-group variant keeps the token in the text only (lines 20-25).
- No production fix was made.

## Findings

**P1:** none.

**P2-1 — The report's text on the empty group and trailing-equals variants is out of date and incomplete.** Report lines 21-23 and 27.
- The report describes the empty delimiter group as "keeping both =", with the render still to be checked.
- `grouped-rt-render/page-4.png` shows a **stray ")" before the "="** in row 2.
- `checkpoint.json:18` and `trailing-equals-result.json:8` already mark this variant as rejected.
- A fifth variant, trailing-equals, exists (`relation-trailing-equals.docx`, `relation-trailing-equals-rt/`, `trailing-equals-result.json`) but:
  - it is not in `probe_leading_relation.py:10`;
  - it has no generator script and no input hash;
  - the report does not mention it.
- Its result keeps the = but **merges rows 1 and 2, leaving only 2 rows** (`trailing-equals-result.json:4-7`); `checkpoint.json:19` rejects it.
- `claude-review/render-delta.md:1` says only "headless preserved, render/UI pending" and leaves out the row merge.
- **Fix:** update the report so both variants are recorded as rejected, with the reasons. Add the trailing-equals generator, or mark that variant as unreproducible.

**P2-2 — The `m:nor` variant may be malformed, so "nor loses =" is not a reliable negative.** `probe_leading_relation.py:13`
- `leading.insert(len(leading)-1, pr)` puts the new `m:rPr` directly before the last child, `m:t`.
- If the run copied from the converter already has `w:rPr`, the new `m:rPr` ends up after `w:rPr`, which is the wrong schema order. If the run already has its own `m:rPr`, the result has two.
- I could not open the ZIP to check which case applies.
- **Fix:** insert at index 0, or merge into the existing `m:rPr`, then validate the XML before reading anything into the result.

**P2-3 — A control that matters for any decision is missing: the original box removed, with no eqArr.**
- The baselines keep the converter's outer `m:box` no-break wrapper; the candidates both drop it and add the eqArr (`build_real_probes.py:32,40-43`).
- In Word, none of the baselines wraps. EXP runs about 30pt past the text margin; this is my rough estimate from the contact sheet. INT and CHEM run off the page.
- As a result, the spike cannot show whether Word would wrap these real formulas automatically once the box is removed, i.e. whether explicit rows are needed at all for Word.
- The report acknowledges this (line 7). Any decision between inserting rows and dropping the box depends on running this control.

**P3-1 — The EXP baseline overflow figure applies only to the headless render.** Report line 9 / `checkpoint.json:9`
- "Beyond the margin by about 2.3pt" matches the LibreOffice headless control render.
- In Word, the same baseline goes well past the margin, though it stays on the page (`word-ui-contact.png`, page 1).
- State which renderer the figure comes from.

**P3-2 — Gaps in the verifier.** `verify_saved.py`
- Line 9 normalizes − to "-" before comparing, so a Writer change from U+2212 to a hyphen-minus would not be caught. Report the raw differences separately.
- Line 19 writes `UI_reopen_not_inferred_from_XML: true` for Writer as well, but there is no field saying `writer_reopen_done: false`. The machine-readable record does not encode the UI debt.
- Line 21 resolves `Path(c[key])` against the current working directory, so the script must be run from ROOT.
- No hash of the UI files after editing is recorded. Also, `~$rd-real-wrap-ui.docx`, a Word lock file, is still in the folder, so the Word file may still be open or the lock is stale. Hash the final UI files.

**P3-3 — Other limits of the probe and the evidence**
- `probe_leading_relation.py:30` reads `maths[3]` after the round trip without asserting that there are 6 oMath. It also checks only `count('=')==2`, not the row count or structure. That check is exactly how trailing-equals "passed" while its rows merged.
- Writer drops only the leading =; the leading −, + and → in EXP and CHEM survive. The result should not be generalized to "relations".
- The LibreOffice control render shows the leading = on import (`control-render/contact.png`, page 4). This suggests the loss happens on DOCX export, but that is not proven.
- Provenance is positional only (paragraph index and ordinal). The OMML is not checked against the MTEF content of the BIN.
- In Word, the candidate rows are centred relative to each other (no `m:aln`); in LibreOffice they are left-aligned. Nothing has been claimed about alignment, and nothing should be.

## UI debt (pending unlock; this review does not cover it)

- Reopen the saved Writer file, check how INT row 2 actually renders, and export a PDF.
- Run any grouping variant through save/close/reopen in the UI. Both current variants are rejected, so the next one needs a fresh approach, for example through Commands, as `checkpoint.json:16` notes.
- Open the Writer-saved copy in Word and look for placeholders or stray glyphs.

## Inspected

- **Report:** `docs/working/codex_dsmt4_real_wrap_2026-11-12.md`, lines 1-29.
- **Requested batch files:** `build_real_probes.py`, `plan.json`, `verify_saved.py`, `saved-structure-check.json`, `probe_leading_relation.py`, `leading-relation-results.json`, `ui-failed-attempt.json`.
- **Requested images:** `word-ui-contact.png`, `word-ui-page-4.png`, `word-ui-page-6.png`, `control-render/contact.png`.
- **Extra, read for consistency:** `grouped-rt-render/page-4.png`, `checkpoint.json`, `trailing-equals-result.json`, `claude-review/render-delta.md` (via grep), `handoff.md` line 9 (via grep), and directory listings.

## Not inspected

- The DOCX/ZIP XML itself, including the run structure behind the nor finding.
- The PDFs and `word-real-reopened.pdf` as text.
- Other individual page images:
  - `word-ui-page-1/2/3/5`;
  - control-render pages 1-6 one by one (I saw them only in the contact sheet);
  - `grouped-rt-render` pages 1-3, 5 and 6.
- `headless-control-metrics.json`, `pre-ui-verification.json`, the `run.json` files, and the rest of `claude-review/`.
- The source exams' own render and full-exam layout.
- Production code, the old corpus, and earlier batches.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no production change.
