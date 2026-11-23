# Clean leading-relation experiment: review (2026-11-12, read-only)

**Scope:** I read:
- the report (lines 1-35);
- `probe_utils.py`, `build_prepared_baseline.py`, `build_wrap.py`, `reopen_saved.py`, `verify_probe.py`;
- `wrap-plan.json`, `verification-with-baselines.json`, `observations.json`;
- the binary and version lines of all four `*-run.json` files.

I viewed no PNGs or PDFs and opened no ZIPs. The rendered outcomes are taken from the PDF text the verifier extracted and from Codex's observations.

**Verdict:** No P1 or P2 issues. The measured claim is narrow, backed by the artifacts, and scoped correctly. Three P3 hardening items remain.

## Validated

**The baseline check is honest.**
- The untouched raw sidecar is recorded as **not** clean: its Commands are `b newline = newline c newline = newline 2,5`, and its saved presentation has 0 equals (`verify_probe.py:7-13`; `verification-with-baselines.json:4,6-17`).
- The W-only prepared single form is clean: Commands `{ b = c = 2,5 }`, 2 equals. That cleanliness is stated as applying to this prepared import only (report lines 9-11).
- `prepare()` is asserted to apply exactly `['W']` (`build_prepared_baseline.py:6`; `verify_probe.py:31`).

**The input is constructed correctly.**
- The cut is fixed before the second top-level `=` (`build_wrap.py:7`).
- Flattening the rows restores the exact signatures of the source children (`build_wrap.py:11`; `verify_probe.py:23-25`).
- Row 2 of the raw split starts with `mo "="` (`verify_probe.py:26`).
- Rule L is asserted to apply exactly `['L']`, and removing the single empty `mrow` gives the raw split tree back exactly (`build_wrap.py:13-16`; `verify_probe.py:27-30`).
- There is no input annotation, and the ODT member set is asserted (`verify_probe.py:17,22`).

**Exact Commands and XML outcomes.** The verifier asserts the following, and it holds identically in both passes:

| Variant | Commands | Equals in saved presentation | PDF text lines |
|---|---|---|---|
| Clean baseline | `{ b = c = 2,5 }` | 2 | `b=c=2,5` |
| Raw split | `matrix{ { b = c } ## { = 2,5 } }` | **1**: row 2 is `<mrow/><mn>2,5</mn>`, the = is lost | `b=c` / `¿2,5` |
| Rule-L split | `matrix{ { b = c } ## { { } = 2,5 } }` | 2 | `b=c` / `=2,5` |

Sources: `verify_probe.py:32-58`; `verification-with-baselines.json:23-124`.

**The second import is correctly labelled.**
- `saved-reimport.odt` is a byte copy of the first saved ODT (`reopen_saved.py:3`), rendered again with new output directories.
- The objects match exactly across passes (`verify_probe.py:45`), and so do the PDF lines (`:58`).
- The report and the verifier say this reimports Writer's own dual representation. It is not a presentation-only import, not GUI, and not an editability test (report line 29; `verification-with-baselines.json:22`).
- Worth noting, and already reflected in report line 25: in the raw split, Writer's own saved file is internally inconsistent. The annotation has `= 2,5` while the presentation has none, and the second import fails again because the annotation is used.

**Binary provenance.** Every run records `/Applications/LibreOffice.app/…/soffice`, `LibreOffice 26.8.0.3 bce0998…`, with no bundled alpha (`*-run.json:2-3`; `probe_utils.py:32-43`).

**Overclaim boundaries hold.**
- Line 25 scopes the result to this one genuine, short sidecar.
- It explicitly excludes a general mtable policy, left alignment, and long-formula wrapping.
- No GUI, editability, semantic, DOCX, serializer or promotion claim is made (lines 15, 29, 35; `observations.json:7-8`).

## Findings (P3)

**P3-1 — Nothing checks that the gated baseline is the same input used for page 1.**
- The report says the W-only baseline was inspected *before* `build_wrap.py` ran (line 11). Only `observations.json:4` and a literal `baseline_gate` string (`build_wrap.py:20`) support that order.
- `verify_probe.py` checks the outputs of `prepared-baseline` but does not hash `prepared-baseline.odt`, and does not assert that its `Object 1` equals the `clean-baseline` bytes in `leading.odt`. They should be identical, since both come from `prepared-baseline-prepared-single.mathml`.
- **Fix:** record the prepared-baseline input hash and assert byte equality. Optionally, have `build_wrap.py` refuse to run unless the prepared-baseline saved Commands equal `{ b = c = 2,5 }`.

**P3-2 — Fresh profiles are claimed but not enforced.**
- `render()` creates the output directory with `exist_ok=False`, but never asserts that `…-profile-{fmt}` did not already exist (`probe_utils.py:36-37`).
- The stems are unique, so the profiles were very likely fresh, but the "fresh profiles" claim (lines 17, 29) is not guaranteed by the code.

**P3-3 — Code version and source mapping are not pinned.**
- No hash of `scripts/transpect/prepare_libreoffice_mathml.py` is recorded in this dirty tree. The previous spike's `dependencies.json` pattern would cover it.
- The mapping "manifest line 202 → `image282.wmf`" (line 7) is stated but not checked by the verifier. It is correctly described as existing sidecar provenance.

## The measured result versus general claims

**Measured (system 26.8.0.3 headless, ODT, one short genuine sidecar `b=c=2,5`, after a clean W-only baseline):**
- a manual split that leaves a row starting with `=` fails on import (¿, and the = is lost from the saved presentation);
- the existing rule L, which adds one empty `mrow`, prevents that failure; the result is stable across one reimport of Writer's own saved ODT.

**Not established:**
- that wrapping was needed at all — `b=c=2,5` fits the 180pt column easily, so the split is purely diagnostic;
- automatic break selection or width inference;
- left alignment — no x0 was measured, and `prepare()` itself flags table alignment as untested;
- longer or nested shapes, tall formulas, page edges, full-exam placement;
- the DOCX route, where `{}` is known to be lost;
- editing in the GUI, or semantic or source acceptance.

**Status:** scratch only. Corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged, no production change, serializer, commit or push.
