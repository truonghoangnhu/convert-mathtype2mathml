# Leading-relation presentation and fraction sidecar: review (2026-11-12, read-only)

**Scope:** I read:
- the report (lines 1-36);
- `probe_utils.py`, `build_presentation.py`, `build_fraction_baseline.py`, `build_fraction_wrap.py`, `build_fraction_presentation.py`, `verify_probe.py`;
- `verification.json` (saved-output details), `observations.json`, `fraction-baseline-observation.json`.

I rendered nothing and viewed no PNGs or PDFs. Statements about what is visible on the pages (red markers, stacked fractions) rely on Codex's recorded observations. Statements about XML, Commands, hashes and PDF text or glyph origins come from my reading of the verifier's assertions and its recorded output.

**Verdict:** No P1 or P2 issues. The claims are backed by the artifacts and scoped to the two short genuine sidecars. One P3 remains: two visual claims are not checked by machine.

## Validated by my own reading of the code and records

**Scalar presentation-only controls (`b=c=2,5`)**
- **Source pinned.** The source is the confirmed saved ODT from the previous run, with its hash and the sidecar hash pinned and rechecked (`build_presentation.py:3,14`; `verify_probe.py:14-17`).
- **Deletion is exact.** Each annotated variant matches its saved source object by signature: Object 3 for prepared, Object 2 for raw (`verify_probe.py:25`). Each stripped variant is byte-equal to the annotated one with exactly one annotation removed, and contains no annotation (`:26-27`; `build_presentation.py:9-12`). No `prepare()` is reapplied.
- **Positive pair.** The two saved outputs are byte-identical (`verify_probe.py:29`). Commands are `matrix{ { b = c } ## { { } = 2,5 } }` for both, with 2 equals (`verification.json:13-19`). The extracted glyph origins and font sizes are equal (`verify_probe.py:76-80`), and the PDF text is `b=c` / `=2,5` on both pages (`:81`).
- **Negative control.** Raw annotated gives `b=c` / `¿2,5` with 1 equals. Raw stripped gives `b=c` / `2,5` with Commands `matrix{ { b = c } ## { { } 2,5 } }` and 1 equals (`verification.json:22-29`; `verify_probe.py:31,81`).
- The report's rejection of the raw stripped form is exactly right (line 18): it renders cleanly only because the = was already lost.

**Fraction sidecar (`P = 72/720 = 1/10`)**
- **Source shape asserted.** The children are `mi, mo, mfrac, mo, mfrac`, with both `mo` being `=` (`build_fraction_baseline.py:7-8`).
- **Mapping and versions pinned.** The single matching manifest line is pinned and rechecked against the sidecar name (`:11-13`; `verify_probe.py:37-39`). The hashes of `prepare()`, the helper and the source are pinned and rechecked (`:36,40-41`).
- **The baseline gate is now enforced by code.** `build_fraction_wrap.py` refuses to build unless:
  - the source and baseline-input hashes match;
  - the observation record exists;
  - the saved Commands are exactly `{ P = { frac { 72 } { 720 } } = { frac { 1 } { 10 } } }`, with 2 `mfrac` and 2 equals (`:6-12`).

  The *content* and timing of the observation are still human-recorded (`fraction-baseline-observation.json`).
- **Baseline bytes are linked.** `fraction-baseline.odt` Object 1, `fraction-leading.odt` Object 1 and the W-only MathML are byte-equal (`build_fraction_wrap.py:24`; `verify_probe.py:46-47`).
- **The split is constructed correctly.**
  - The cut is before child 3, and flattening restores the exact source signatures (`build_fraction_wrap.py:15-18`; `verify_probe.py:51-52`).
  - Row 2 of the raw split starts with `=` (`:53`).
  - Rule L is exactly `['L']`, and removing the single empty `mrow` gives back the raw split (`:54-57`).
  - The inputs have no annotation (`:50`).
- **Determinism.** The current `prepare()` reproduces the W baseline and the L split byte for byte (`verify_probe.py:43,58`), and the earlier scalar artifacts too (`:66-68`). This closes my earlier optional suggestion.
- **Outcomes.**
  - Equals counts are `[2,1,2]` for baseline, raw split and L split.
  - The `mfrac` signatures in all three saved outputs equal the source (`verify_probe.py:60-61`).
  - The raw split's PDF text contains ¿ and the L split's does not (`:82`).
  - Commands are as recorded (`verification.json:54-72`).
- **Fraction presentation-only pairs.** Both the single pair and the split pair have byte-identical saved outputs (`verify_probe.py:29-30`), equal glyph origins and sizes (`:80`), and 2 equals each (`:31`). The split's Commands keep `{ } =` after a presentation-only reimport (`verification.json:43-52`).

**Run provenance.** All four runs use system 26.8.0.3 `bce0998…`, return code 0, and a profile asserted absent before launch (`probe_utils.py:37-38`; `verify_probe.py:84-87`). There is no bundled alpha.

**Boundaries.** Report line 36 limits the result to two short sidecars with manual cuts. It explicitly excludes:
- a general mtable or left-alignment policy;
- a serializer or generator;
- natural wrapping, tall, page-edge or full-exam cases;
- DOCX/Word;
- GUI and semantic acceptance.

## Finding

**P3-1 — Two visual claims about the fraction outputs are not checked by machine.**
- **"No visible red marker"** for the four `fraction-presentation` pages (report line 28) and the `fraction-leading` baseline page rests only on `observations.json:5-6`. The verifier asserts no ¿ only for `fraction-leading` page 3 (`verify_probe.py:82`). Glyph equality within each pair (`:80`) would still pass if both pages in a pair had ¿.
- **"Retain … the stacked fractions"** for the `fraction-presentation` outputs (line 28) is backed by the Commands strings, but the `mfrac`-signature-against-source check is applied only to the `fraction-leading` outputs (`:61`).
- **Fix:**
  - assert `not any('¿' in s …)` for all four `fraction-presentation` pages and for `fraction-leading` page 1;
  - apply the `mfrac` signature check (`:61`) to the four `fraction-presentation` outputs too.

  Both checks are cheap and need no new run.

## What the measurements support, and what they do not

**Supported (system 26.8.0.3 headless, ODT):**
- for these two genuine sidecars, after a clean W-only baseline, a leading-`=` row fails with the raw split and imports cleanly with the existing rule L;
- the saved L output (and the scalar prepared output) is a **fixed point under presentation-only reimport**: identical bytes, Commands and glyph origins;
- the raw path loses the = irreversibly, even when the result renders cleanly.

**Not supported:**
- any general mtable, width, wrapping or left-alignment rule;
- semantic or source equivalence;
- GUI editability;
- the DOCX route.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no production change, commit or push.
