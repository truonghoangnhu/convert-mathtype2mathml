# DSMT4 real-wrap: closure review of the Commands capture and binary comparison (2026-11-12, read-only)

**Scope:** I reviewed only the closure evidence:
- report lines 83-99;
- `commands-ui-observations.json`, `import-version-comparison.json`, `commands-second-save-headless/result.json` and `checkpoint.json`;
- one grep for binary or version records.

I viewed none of the new page-4 PDFs. Every visual statement below is Codex's observation and I do not certify it.

**Verdict:** No P1 issues. Both previous P2 findings are closed. The previous P3 findings are closed or reduced to a minor follow-up. Two scope gaps of substance remain, both P3. There is still no production change, no generic fix and accepted stays 0.

## Previous findings: closure

| Previous finding | Status | Evidence |
|---|---|---|
| **P2-1: the "error on import" claim conflicted with the earlier headless render** | **Closed** | A byte-identical copy of the control opened in the LibreOffice 26.8.0.3 UI shows the red relation marker *before* Math is activated, and again after (report line 93; `import-version-comparison.json:3-4,8-9`). The same system binary run headless with a fresh profile is also red, on the control and on the Writer-saved DOCX (lines 10-11). The bundled `LibreOfficeDev 26.8.0.0.alpha0 2c87e51…` renders the same control with a clean = (lines 6, 12). The report scopes this correctly as a per-binary difference on one input, not a cause in the source code or a version recommendation (line 95; `import-version-comparison.json:14`). |
| **P2-2: "only `{}` added" was not shown** | **Closed** | The `originalCommand` string captured from the AX tree before the edit already contains `S"="`, `"+"1` and `"|"` (`commands-ui-observations.json:3,7`). The pasted string differs from it only by `# = int` → `# {} = int` (lines 4-5). I compared the two strings and they agree. The pasted string also matches the ODT annotation (`commands-odt-annotations.json:14`). The report correctly limits this to a delta against the captured AX text, not proof that the OMML structure is unchanged (line 87). One caveat: the observations are transcribed from the CUA tool output (line 2), not stored as a raw machine capture. |
| **P3-1: Word cross-render hash and linking UI observations to the record** | **Closed** | `word-commands-cross.pdf` is now hashed (`import-version-comparison.json:42-44`). The Word SHA before and after is linked and equal (`commands-ui-observations.json:12-14`). |
| **P3-2: `checkpoint.json` out of date** | **Closed** | Lines 15-16, 21, 22 and 29-34 are updated. The minor leftover is in P3-1 below. |
| **P3-3: stability over a second save** | **Closed for headless; the UI step is still open** | A second save with system 26.8.0.3 headless, on a fresh copy, drops the leading = again: two equals become one, and the three rows remain (`commands-second-save-headless/result.json:6-8`). Line 99 correctly says no second UI save was run. |

## Remaining scope gaps

**P3-1 — Older render evidence does not record which binary produced it.**
- The grep finds binary or version records only in `probe_leading_relation.py`, `review-v2/probe_controls.py` (system `/Applications/…/soffice`) and `import-path-headless/bundled-control/run.json`.
- There is no generator or version record for `control-render/`, `grouped-rt-render/`, `trailing-rt-render/`, the earlier `headless-control-metrics.json`, or the Writer headless render of the unboxed control.
- Line 95 says the old canonical render is explained by the bundled binary. That fits, because the old `control-render/page-4.png` I viewed shows a clean =, matching the bundled result. But it is an inference, not a record. The conclusions affected:
  - the "EXP +2.3pt" figure (`checkpoint.json:9`);
  - the stray ")" that led to rejecting the empty group;
  - the claim that the unboxed INT/CHEM still clip in Writer headless.
- **Fix:** tag those renders as produced by an unrecorded binary, probably the bundled one, or check the PDF Producer metadata. The rejections stand regardless, because each variant fails on other grounds as well: `{}` is lost through DOCX, and trailing-equals merges rows.

**P3-2 — The quoted operators are a Writer fidelity issue in their own right, not only a provenance detail.**
- The Commands text that 26.8.0.3 imports for the INT eqArr turns `=`, `+` and `|` in rows 1 and 3 into quoted *text* (`commands-ui-observations.json:3`).
- The baseline's import of the same source runs has unquoted operators (`commands-odt-annotations.json:38`).
- Whether this comes from the eqArr context or from the split runs has not been isolated. Either way, it is a second Writer import difference for the explicit-row strategy, beside the leading-relation parse error.
- **Fix:** record it as an open observation in the policy notes. Do not let it drop out of view now that provenance is settled.

**Accepted as residual debt for this scratch spike, not blocking closure:**
- the second save was not run through the UI;
- only one formula was tested, in an artificial 180pt column;
- there is no full-exam or source-fidelity check;
- the inherited empty integral operand (□) and plain "2e" in CHEM remain;
- Word's save still turns U+2212 into "-" (`checkpoint.json:23`).

## Remaining actual defects (product or application behaviour)

1. **LibreOffice 26.8.0.3 (system UI and headless):**
   - an eqArr row that starts with a relation imports as unparseable Commands and renders a red marker;
   - DOCX export drops the `{}` workaround;
   - each further DOCX save drops the =.
   - The bundled dev alpha binary renders this case cleanly. The cause in the source is unknown.
2. **The `{}` workaround persists only in ODT** (UI reopen, Codex observation; report line 75). It does not survive DOCX.
3. **Writer does not auto-wrap long single-line OMML**, whether the box is present or not.
4. **Inherited:** the empty integral operand, and the plain "2e" in CHEM.

## Next safe boundary

This agrees with `checkpoint.json:22`.

- **Allowed next step:** a target-specific MathML→ODF wrap spike for Writer, in scratch, on the same INT formula. Record the binary and version in every run and render. Treat the explicit rows as structure (a stack/mtable from MathML), not as an OMML trick.
- **Not allowed:** a shared OMML workaround (`{}`, an empty `m:d`, trailing relations), any converter or normalized-MathML change, any version recommendation, or any change to the support policy beyond an approved note that "row-leading relations in eqArr are unsafe in Writer via DOCX on 26.8.0.3".

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips and Lý ¶91 unchanged, no production edit, commit or push.

**Not inspected:**
- every new PDF and page image: the two UI import PDFs, the three headless renders, `word-commands-cross.pdf` and the ODT reopen PDF;
- the XML inside the DOCX and ODT ZIPs;
- the raw CUA capture archive;
- `import-path-headless/bundled-control/run.json` beyond the grep hit;
- the prior review document, which I did not reread;
- the LibreOffice source code.
