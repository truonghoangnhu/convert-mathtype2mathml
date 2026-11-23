# DSMT4 MathML→ODF wrap: final UI delta review (2026-11-12, read-only)

**Scope:** I read the banner (line 1) and lines 29-48 of the report, `exp/UI-verification.json`, `checkpoint.json` and `construction-verification.json`, and I viewed `exp/UI-exp-contact.png`.

I did not view `UI-exp-4.png` or the PDF, and I did not reread my earlier review document. What I say about pixels comes only from that one contact sheet and does not certify the render.

**Verdict:** The narrow claim is supported. There are no P1 or P2 issues and no new blockers. The EXP UI step is closed **only for the unary-continuation case**. Accepted stays 0 and there is no production change, commit or push.

## The narrow claim (confirmed)

**Commands before and after.**
- The string captured on import (`UI-verification.json:3`) and the string after reopen (`:4`) differ **only** in `200000` → `200001`. I compared them character by character.
- Object 3, the unedited table, still has `200000` (`:22`). Object 4 has `200001` (`:28`).
- So only Object 4 was edited; the other three objects only went through the document-level save and reopen (report line 46).

**Real UI run.**
- The original MathML-only EXP input was opened in installed Writer **26.8.0.3**. It was then saved as a new ODT, closed, reopened through Recent Documents, and exported to PDF.
- The ODT and PDF hashes are recorded (`UI-verification.json:32-43`).
- This run is separate from the bundled renderer (`…/dependencies/bin/override/soffice`, 26.8 alpha) (report lines 13, 43).

**What I see on the contact sheet, all of which matches the report:**
- Page 4: 3 rows ending `+200001`, with the AFTER sentinel below and no red marker.
- Page 3: `+200000` (not edited).
- Page 2: prepared-single is one line.
- Page 1: raw-single breaks into vertical tokens with red ¿.
- Continuation rows are centred or indented, not left-aligned. The report states this as unresolved (lines 35, 46).

**The scope limits in line 48 are correct.** Not covered:
- leading relations;
- choosing break points automatically;
- semantic equivalence with the full source;
- placement in the source exam;
- tall fractions and page-edge cases;
- INT.

The status stays `needs_review`.

## Prior findings: status

| Prior finding | Status |
|---|---|
| **P2-1:** the bundled INT result was missing; INT is inconclusive for wrapping | **Closed.** The report now says INT fails before wrapping and is inconclusive for mtable wrapping, and that the bundled render matches the UI (line 31; `checkpoint.json:4`). |
| **P2-2:** EXP covered neither the UI nor a leading relation | **Closed.** The UI step is now done. The unary-only limit is stated (lines 33, 48). |
| **P3:** the two EXP tables are the same input | **Closed** (line 33). |
| **P3:** alignment | **Disclosed.** It remains an open limit (line 35). |
| **P3:** EXP raw-single ¿ markers omitted | **Closed** (line 33). |
| **P3:** verifier and provenance records | **Addressed.** The verifier now checks the prepared-single tokens and the embedded object content, and `dependencies.json` and `annotation-provenance.json` were added (line 37). The `refs.json` mapping is stated as positional and not validated. That is acceptable for scratch work. I did not inspect those two new files. |

## Remaining limits (informational, not blockers)

- **The reopen read Writer's own saved ODT, not a second MathML-only import.**
  - The saved file stores StarMath annotations (`UI-verification.json:6-31`).
  - The pipeline-relevant MathML import was the *first* open (Object 4 imported as a 3-row `matrix{…}`). The reopen shows that the edit persists in Writer's own format.
  - Worth one clause in the report. No rerun is needed.
- **Left alignment, leading relations, and INT's input parse failure remain open** (`checkpoint.json:21`).
- **Minor housekeeping:** the heading at line 21 still reads "UI pending" (the banner corrects it), and `checkpoint.json:7-18` lists only the INT files (the EXP files are in `UI-verification.json`). Optional to tidy.

## Status

Scratch only.
- INT is a negative result and inconclusive for wrapping.
- EXP passes the narrow unary-continuation UI round trip in 26.8.0.3, with left alignment unresolved.
- Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged.
- No production change, commit or push.

No corpus rerun is needed, because nothing in production changed.
