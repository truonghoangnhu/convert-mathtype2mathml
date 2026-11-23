# DSMT4 real-wrap: review of the Commands/ODT delta (2026-11-12, read-only)

**Scope:** I reviewed only the new section of the report (lines 69-81), `commands-control-result.json`, `commands-control-verification.json`, `commands-odt-annotations.json`, `verify_commands_control.py` and `checkpoint.json`.

I did not view the three new page-4 PDFs, so I am not certifying their pixels. I did reread one older artifact, `control-render/page-4.png`, to check the new import claim. The credit was available, and I wrote or executed nothing.

**Verdict:** No P1 issues. The format comparison holds within its scope:
- With `{}` added in Commands, the ODT survives save, close and reopen; the DOCX does not.
- No production change was made, no generic fix proposed, and accepted stays 0 (report line 81; `checkpoint.json:13-14`).

Two P2 findings limit how far the diagnosis can be read. Neither changes the conclusion that nothing goes to production.

## Supported, within scope

- **XML check of the Commands DOCX.**
  - The six formula texts match the control and INT still has 3 rows (`verify_commands_control.py:10-12`).
  - The control SHA `0d637f…` matches `plan.json`, and the earlier QA file's SHA `9b2f…` is unchanged (`commands-control-result.json:6,13`).
- **The ODT keeps `# {} = int`** in the annotation of Object 4 (`commands-odt-annotations.json:14`; `verify_commands_control.py:13-14`).
- **What the XML check cannot show.** Two equals signs in the DOCX XML do not mean Writer reimports it correctly. Codex observed after reopen that `{}` is gone and the Formula AX shows ¿ (`commands-control-result.json:2,28`; `commands-control-verification.json:2,6`). The report does not count the preserved = as a success (line 73).
- **What the ODT result does and does not prove.** It shows that Writer's own format keeps the StarMath syntax. It does not show that the project's MathML→ODF route handles a leading relation. Line 81 says this route must be tested independently.
- **Word cross-render.** It is render-only, with no Word edit or save (line 77).
- **Inherited operand.** The empty first integral operand (□) is still there (line 75; `checkpoint.json:10`).

## Findings

**P1:** none.

**P2-1 — The new claim that the error already exists on import conflicts with an earlier render and needs a narrower scope.** Report line 71.
- The claim rests on Codex's UI observation of Commands and the AX Formula before the edit: `# = int` with ¿. None of the JSON artifacts records this pre-edit observation; `commands-control-result.json:27` covers only the state after adding `{}`.
- The earlier **headless** render of the *untouched control* (`control-render/page-4.png`, which I viewed) draws row 2 as a clean **"= ∫₀¹ …" with no ¿**.
- Meanwhile Codex's UI PDF of the reopened Commands DOCX reportedly shows a red ¿.
- So in the evidence so far, OMML with a row-leading = produces a Commands string the StarMath parser flags, yet draws = correctly in at least one import path. Two explanations have not been separated:
  - the headless and UI paths behave differently;
  - the OMML Writer exported is structurally different from the control's (line 73 cites `…docx.math4.xml`, but no generator is shown and no diff against the control row exists).
- **Fix:** rephrase line 71 as: "on import, the Commands text is not parseable at the leading =; whether it renders as ¿ depends on a path or structure not yet isolated". Do not extend the previous "export-only" hypothesis into "the cause is import".

**P2-2 — "Only `{}` was added" is not shown.** Report lines 73 and 79.
- Line 79 says Codex replaced the **entire** Commands text with a pasted Unicode string after a failed typing attempt.
- The ODT annotation for Object 4 contains operators in quotes: `S"="`, `"+"1`, `"|"` and `−3` (`commands-odt-annotations.json:14`). The same operators are unquoted in Writer's own import of the INT baseline (Object 3, line 38). Rows 1 and 3 of the original Object 4 are byte-identical copies of the baseline's runs (`build_real_probes.py:36`), so these quotes very likely came from the paste, not from import.
- In StarMath, quoted `"="` and `"+"` are text, not operators. That can change spacing and how they export (`m:nor`/`sty` rather than an operator). `verify_commands_control.py:11` compares only `m:t` text, so it cannot detect that kind of change.
- **Fix:** record the Commands text before the edit and the exact pasted string, and show the diff. Until then, describe the control as "Commands rewritten, including `{}`", not "only `{}` added".

**P3-1 — Records not linked to the UI steps.** `verify_commands_control.py:15`
- The UI observation strings ("failed…", "PDF inspected") are hardcoded again. Load them from a record of the observation, as `verify_saved.py` now does.
- `word-commands-cross.pdf` is not hashed anywhere.
- The claim that the DOCX SHA was unchanged after Word opened it (line 77) depends on the verifier having run after Word closed, and nothing records that order. Record the hash before and after the Word view.

**P3-2 — `checkpoint.json` is out of date.**
- Line 16 still says "investigate … relation export".
- Line 15 (`new_failure`) does not mention the parse state on import.
- Line 21 points to the first review, not the reopen review.
- Lines 4-8 do not list the new Commands, ODT and PDF artifacts.

**P3-3 — Stability over a second save is not tested.** If reopening the DOCX brings back `# = int` (the error state), another Writer save of that file would probably drop the = again, as in the original QA file. This predicts the "not durable" point in line 81. Testing it once would turn the prediction into evidence.

## Remaining actual defects (not reporting issues)

1. **Writer cannot keep a row-leading relation in an OMML eqArr through DOCX.** On import the Commands text is `# = …`, which does not parse. On export the `{}` workaround is dropped, and if no workaround is present the = itself is dropped (earlier QA file). How the error renders varies (P2-1).
2. **Writer does not auto-wrap long single-line OMML** (the INT and CHEM baselines clip). This is unchanged.
3. **Inherited problems:** INT's empty integral operand, and the plain "2e" in CHEM.
4. **Word's save normalizes U+2212 to "-".** The downstream effect is unverified (`checkpoint.json:23`).

## Next safe experimental boundary

Stay in scratch, on this single INT formula. Make no change to the converter, normalized MathML/OMML or the support policy.

1. **Separate path from structure.**
   - Render `writer-commands-leading-ui.docx` headless with an isolated profile and compare its page 4 with `control-render/page-4.png`.
   - In the UI, open the *untouched* control and export a PDF without editing it.
   - Diff the OMML of row 2 between the control and the Writer-saved DOCX.
2. **Record the exact Commands text** before and after the edit, and redo the `{}` test as a true single-token insertion with no full paste.
3. **Run a second Writer save** of the Commands DOCX as a negative control.
4. **Decide on policy only after steps 1-3, and per target only.**
   - Word: OMML (box removed, wraps without eqArr; render-only evidence).
   - Writer: the existing MathML→ODF route, tested separately for a leading relation.
   - Do not inject `{}`, an empty group or a trailing relation into shared output.
   - At most, document "row-leading relation in eqArr is unsafe in Writer via DOCX" as a known limitation, after approval.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no commit or push.

**Not inspected:**
- `writer-commands-leading-reopened.pdf`, `writer-commands-leading-odt-reopened.pdf`, `word-commands-cross.pdf` and any page images made from them;
- the XML inside the DOCX and ODT ZIPs, including `…docx.math4.xml`;
- report lines 1-58 beyond the section headings;
- the prior reopen review document;
- the LibreOffice source code.
