# EXP annotation-authority experiment: review (2026-11-12, read-only)

**Scope:** I read the report (lines 1-21), `build_probe.py`, `verify_probe.py`, `run_headless.py`, `plan.json`, `system-run.json`, `verification.json`, `divergent-annotation.mathml` and `saved-with-annotation.mathml`.

I did not view the `system-page-*.png` files, the PDF, or the saved ODT ZIPs. Visual statements are Codex's.

**Verdict:** No P1 issues. The authority result is well constructed and backed by real artifacts, not only pixels. There is one P2: the presentation-only reimport changed the formula's structure, and neither the report nor the verifier says so. That directly affects any claim that the two representations correspond. The rest are P3.

## Validated

**The divergent control is built correctly.**
- The divergent variant has byte-identical presentation to the matching original (`build_probe.py:38`; `verify_probe.py:15`).
- Its annotation differs by exactly one change, `200000` → `200009` (`build_probe.py:13-14`; `verify_probe.py:16`).
- `divergent-annotation.mathml` shows this directly: the presentation `<mn>200000</mn>` sits beside an annotation with `+ 200009`.
- It is labelled never to be used as conversion output (report line 5; `build_probe.py:1`).

**Authority is shown in two independent places:**
- Writer's saved Object 2 has **only** `200009` among its numbers and in its annotation (`verification.json:15-24`).
- The PDF text on page 2 contains `+200009` and has exactly three formula rows (`verify_probe.py:35-37`).
- So for this EXP control, system 26.8.0.3 takes the constant from the StarMath annotation. Report line 11 scopes this correctly.

**The presentation-only control is built correctly.**
- Variant 4 equals Writer's saved Object 4 with only the `annotation` element removed (`verify_probe.py:17-19`).
- The source ODT hash `7b0993…` (`plan.json:22`) matches the earlier `align-writer-edited.odt`.

**The alignment loss is shown in the artifacts.**
- Writer's saved Object 4 has **no `alignl`**, while Objects 1-3 have it (`verify_probe.py:28`; `verification.json:39`).
- The PDF x0 values are `[110.7, 115.3, 125.15]`, a 14.45pt spread, against zero spread on pages 1-3 (`verification.json:49-85`).
- So `mtd columnalign="left"` does not carry the alignment through a presentation-only reimport.

**Binary and run record.** System `/Applications/LibreOffice.app/…/soffice` 26.8.0.3 `bce0998…`, headless, with separate fresh profiles (`system-run.json:2-3,8,26`; `run_headless.py:10-14`). It is not the bundled alpha.

**Limits are stated clearly.** The GUI is not claimed and the blocker is recorded (report lines 17-19). There is no generator, no `prepare()` change, no production change, and accepted stays 0.

## Findings

**P2-1 — The presentation-only reimport changed the structure. The report omits this, and the verifier checks only numbers.**
- The original Commands are `matrix{ alignl { P left ( t right ) = 2000 e ^ { 0,1 t } } ## alignl { - 5000 e ^ { - 0,03 t } } ## …}`.
- Reimporting Writer's own saved MathML **without** its annotation gives:
  `matrix{ { P { left ( t right ) = 2000 } e ^ { 0,1 t } } ## { { - 5000 } e ^ { { - 0,03 } t } } ## { + 200001 } }` (`verification.json:39`).
- The relation `=` now sits **inside a group** `{ (t) = 2000 }` between `P` and `e^…`. `-5000` and `-0,03` become separate groups.
- This matches the nesting in Writer's exported presentation: `<mi>P</mi><mrow><mrow>(t)</mrow><mo>=</mo><mn>2000</mn></mrow><msup>…` (`saved-with-annotation.mathml:1`).
- So on this artifact, the MathML that Writer itself generates is **not structurally equivalent** to the StarMath it was generated from. Only the annotation keeps the original grouping. Row 3 also moved slightly, from x0 125.05 in the previous run to 125.15 now. That is consistent with a layout change but does not prove one.
- Report line 13 says only that it "keeps all three formula rows and 200001 but loses left alignment". The verifier checks only `mn` values and whether `alignl` is present (`verify_probe.py:25-28`), so it cannot detect regrouping.
- **Fix:**
  - state the regrouping in report line 13;
  - add an assertion comparing the reimported Commands with the original, modulo `alignl`, and record the difference;
  - do not describe Writer's saved MathML/annotation pair as corresponding representations.

**P3-1 — The "existing document unchanged" claim needs a hash recheck.**
- `plan.json:22` records `align-writer-edited.odt` at build time.
- The report says it stayed unchanged after the cancelled GUI dialog (line 19), but `verify_probe.py` does not rehash it after that attempt.

**P3-2 — Human observations are again hardcoded in the verifier output.** `verify_probe.py:42` writes `visual_inspection` and `GUI_blocker` as literal strings. Store them as a separate observation record, as done previously.

**P3-3 — Two smaller gaps in the record.**
- The claim "no cached preview or imported object state" (line 5) is true by how the input was built: it inherits the generated scaffold, which contains only MathML objects. But no check asserts the ZIP name list.
- The failed first sandbox attempt (line 9) is not recorded in `system-run.json`.

## Narrow conclusions versus general serialization policy

**What this experiment establishes (one EXP formula, system 26.8.0.3 headless):**
1. When annotation and presentation disagree, Writer's importer renders and saves the **annotation's** value.
2. Writer's saved MathML with `mtd columnalign` does **not** keep left alignment after a presentation-only reimport.
3. (P2-1) Writer's saved MathML does **not** reproduce the original StarMath grouping when reimported without its annotation.

**What it does not establish:**
- any rule for other annotation encodings, consumers (Word, browsers, other LibreOffice builds) or formula shapes;
- behaviour in the GUI;
- leading relations, tall formulas, page edges or the full exam.

**Implication for policy (direction only, not approved):**
- Any automatic annotation generator must prove that the annotation and the presentation correspond structurally, and must fail closed when they diverge. Writer's silent preference for the annotation hides any divergence.
- Writer's own exported MathML **cannot** serve as the reference for that correspondence, because it regroups the expression (P2-1).
- This experiment does not justify implementing a generator, widening `prepare()`, or changing normalized MathML/OMML. Report line 21 correctly stops short of that.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no production change, no commit or push.

**Not inspected:** the PNGs and PDF, the ODT ZIPs beyond the extracted `.mathml` files, `matching-original.mathml` and `saved-presentation-only.mathml` (their content is covered by the verifier's equality assertions), and the LibreOffice source code.

---

Codex resolution after review (not a second Claude approval): P2 Commands regrouping is now recorded and asserted in verify_probe.py and the report; no semantic inequivalence is inferred from string grouping alone. P3 source hash recheck was already added during the review and passes. Human observations moved to observations.json. Expected ZIP members now asserted; initial sandbox failure recorded as a tool-output observation rather than an invented subprocess log. Updated verifier and git diff --check pass. No production change, corpus promotion, or GUI acceptance.
