# DSMT4 MathML→ODF wrapping spike: review (2026-11-12, read-only)

**Scope:** I read:
- the report (lines 1-25);
- `build_probe.py`, `exp/build_probe.py`, `verify_probe.py`;
- `construction-verification.json`, both `plan.json` files;
- `UI-annotations.json`, `exp/bundled-annotations.json`, `bundled-run.json`, `checkpoint.json`.

I viewed three contact sheets: `exp/bundled-exp-contact.png`, `int-ui-contact.png`, and also `bundled-int-contact.png`, which the report does not mention. I grepped the corpus `refs.json` once, for provenance only. I wrote and executed nothing.

**Verdict:** No P1 issues. Input preservation is checked well, and the claims are mostly narrowed correctly. Two P2 interpretation gaps weaken the INT-versus-EXP contrast. EXP still has no UI evidence: Writer UI edit, save and reopen are **NOT RUN** (Mac locked). The bundled render is headless only and is not UI acceptance.

## Confirmed

**Input preservation**
- Splitting the top level into three `mtr/mtd/mrow` rows keeps the exact signature of every child: tag, attributes, text and descendants (`build_probe.py:16-17`; `verify_probe.py:12`).
- Token order is equal across the raw input, the raw table and the prepared table (`verify_probe.py:10`).
- The inputs contain no annotation (`build_probe.py:23`; `verify_probe.py:14`).
- The hashes of the source sidecar, the input ODT and each variant are rechecked (`verify_probe.py:10,15-16`).
- `raw-single` is byte-identical to the source: its SHA equals the source SHA (`plan.json:4,17`; `exp/plan.json:4,17`).

**Provenance**
- The sidecar ↔ `image223.wmf` mapping is recorded in the corpus (`dsmt4-real-corpus/Toan-So-GD-Tuyen-Quang-lan-1/tmp/refs.json:3695,4409`).
- The OLE ↔ preview link is positional only, and the report says so (line 3).

**Preparation used**
- Only the existing `prepare()` is used, and no StarMath is written by hand.
- For INT it applies rule L: an **empty `mrow` (a `{ }` group) before the = in row 2**. This is not an empty table row, and the annotations still show 3 rows (`plan.json:54-59`; `UI-annotations.json:23`).
- For EXP the prepared table has no changes (`exp/plan.json:54`).

**INT**
- This is a document-level import → Save As ODT → close → reopen in UI 26.8.0.3, with no formula edit (`checkpoint.json:3-4`; report line 15).
- On my viewing of `int-ui-contact.png`:
  - raw-single breaks into vertical tokens with ¿ markers;
  - prepared-single is one line with ¿ markers and clips;
  - both tables collapse into a single clipped line with markers.
- No variant passes, and the report correctly does not generalize (line 17).

**EXP, bundled headless only**
- On my viewing of `exp/bundled-exp-contact.png`:
  - both tables show 3 rows with the sentinel below;
  - prepared-single is one line that roughly reaches the right margin;
  - raw-single breaks into vertical tokens.
- The binary and its version are recorded (`bundled-run.json:2-3`) and kept separate from the UI app (line 42).

**Status:** no production change, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged (report line 25; `checkpoint.json:19-20`).

## Findings

**P1:** none.

**P2-1 — The bundled INT result is missing from the report, and it changes what INT can show.**
- `bundled-int-contact.png` and an INT `bundled-annotations.json` exist. The bundled run log covers the INT input (`bundled-run.json:17,35`).
- On my viewing, the bundled INT render looks **the same as the UI 26.8.0.3 render** on all four pages at contact-sheet resolution: the same markers and the same collapse of both tables.
- So, unlike the earlier OMML leading-relation case, the INT failure is **not binary-dependent** in this evidence.
- Prepared-single, which has no table, already shows ¿ in both binaries. The INT sidecar therefore fails to import cleanly *before any wrapping*; the integral and its operand are separated and the "|" bars appear as `mline` (`UI-annotations.json:11`).
- **Fix:** report the bundled INT result. Classify INT as *inconclusive for mtable wrapping* (the input already fails), not as evidence that mtable fails.

**P2-2 — The EXP "candidate" does not cover the case that failed.**
- EXP passes only on the bundled dev binary.
- Its continuation rows start with a **unary −/+**, not a relation (`exp/bundled-annotations.json:17`).
- So EXP tests neither the installed 26.8.0.3 nor a row that starts with a relation, which is the defect found in the earlier spike.
- The INT/EXP contrast therefore mixes three factors at once:
  - the binary;
  - whether the content parses cleanly;
  - unary versus relation at the start of a row.
- **Fix:** say this explicitly in the report. Read EXP only as "a clean three-row mtable with unary continuations imports on the bundled binary".

**P3-1 — The two EXP tables are the same input.**
- The `raw-table` and `prepared-table` SHAs are identical (`exp/plan.json:45,68`).
- Pages 3 and 4 are therefore one observation, not two.

**P3-2 — Alignment is not preserved, and the report does not say so.**
- `mtable columnalign="left"` (`build_probe.py:12`) imports as a plain `matrix{…}` with no alignment.
- On my viewing, the EXP continuation rows sit centred or indented, not left-aligned.
- `prepare()` itself flags the left-alignment probe as failed (`exp/plan.json:55-60`). The report should state this before calling the result a layout candidate.

**P3-3 — Small omissions and gaps in the record.**
- EXP raw-single also shows red ¿ markers on my viewing; report line 21 says only "vertical token breakup".
- `UI-annotations.json` does not record which file it came from (input, saved or reopened ODT) or which binary.
- `verify_probe.py` does not check:
  - that the `prepared-single` tokens match the raw input;
  - that each ODT `Object i/content.xml` equals its variant file;
  - the `refs.json` mapping between sidecar and `image*.wmf`.
- The hash of `scripts/transpect/prepare_libreoffice_mathml.py` used from this dirty tree is not recorded. The output hashes do pin the result, but not the code that produced it.

## Safe next experimental boundary

Stay scratch-only, on one or two formulas in the 180pt column. Do not change `prepare()` rules, normalized MathML/OMML, converter code or policy, and do not promote anything.

1. **EXP in the UI after unlock (already planned):**
   - open the EXP input in installed Writer 26.8.0.3 and capture Commands as imported;
   - edit 200000→200001 on a QA copy only;
   - save as ODT, close, reopen, capture Commands again, and export a PDF;
   - record the binary and version;
   - record any failure as a failure.
2. **INT: diagnosis only, no repair.** To find which construct produces the ¿ markers, test subsets of the original top-level children as single objects (for example the prefix before the first `mline`, or each integral segment alone). Do not rebind the operand or touch the bars.
3. **Leading relation in mtable:** test this only with a real sidecar whose *single* form imports cleanly on 26.8.0.3 and which has a second top-level `=`. Test raw, then the existing rule L, on both binaries, through a UI save and reopen.
4. **Before any further step:** look again at alignment, which `prepare()` already reports as failing.

**Status:** scratch only. INT failed in the UI and is inconclusive for wrapping. EXP is `needs_review`, its UI is pending unlock, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no commit or push.

**Not inspected:**
- the individual page PNGs, `mathml-wrap-writer-reopened.pdf` and the bundled PDFs;
- the XML inside the ODT ZIPs (saved and reopened);
- the INT `bundled-annotations.json` beyond its existence;
- the source of `prepare_libreoffice_mathml.py`;
- the OLE/BIN semantics.

My pixel statements come from contact sheets at low resolution and do not certify the renders.
