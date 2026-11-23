# EXP MathML→ODF alignment spike: review (2026-11-12, read-only)

**Scope:** I read the report (lines 1-17), `build_probe.py`, `verify_alignment.py`, `plan.json`, `verification.json` and `bundled-run.json`, and I viewed `UI-contact.png`.

I did not view `UI-align-4.png`, the PDFs or the bundled page images, and I did not open the ODT ZIPs. What I say about pixels comes from one contact sheet at low resolution and does not certify the render.

**Verdict:** No P1 or P2 issues. The narrow claim is supported, and the guards match its scope:
- for **one** EXP formula with unary continuation rows,
- a **hand-authored** StarMath annotation with `alignl` makes all three rows flush left in installed Writer 26.8.0.3,
- and this survives one edit, save and reopen;
- MathML `columnalign` on `mtable`, `mtd` or `mtr` has no effect.

Accepted stays 0, and there is no production, annotation-generator, normalized-MathML or OMML change, and no commit or push.

## Validated

**Inputs are controlled.**
- `table-left` is byte-identical to the earlier prepared table, so it is a true baseline (`plan.json:4,9`).
- All four variants share the same presentation signature apart from `columnalign` (`verify_alignment.py:10,14`).
- The embedded object bytes equal the variant files, and the input hash is rechecked (`:14-15`).

**Strongest evidence for the negative MathML result.**
- In both the bundled and the UI-saved ODT, the Commands Writer generated for Objects 1-3 contain **no `alignl`** (`verify_alignment.py:20` asserts this; `verification.json:10-12,20-22`).
- So Writer's MathML importer drops `columnalign` on the table, cell and row, in both binaries. This is evidence from the text Writer stored, not from pixels.

**The UI edit changed only the constant.**
- Object 4's stored annotation after the edit is exactly the planned command with `200000` → `200001`. This is asserted by string equality (`verify_alignment.py:20`; `verification.json:23`).
- Objects 1-3 only went through the document-level save and reopen (report line 7).

**Measurement is consistent and correctly scoped.**
- In the UI PDF, the text-origin x0 values are `[110.7, 115.3, 125.05]` on pages 1-3: identical, with a 14.35pt spread. Page 4 is `[110.7, 110.7, 110.7]`, with zero spread (`verification.json:28-69`).
- Identical x0 values on pages 1-3 confirm that the `mtd`/`mtr` attributes changed nothing.
- The script asserts these values for pages 1 and 4 (`verify_alignment.py:27`).
- These are text origins, not ink or fidelity, and the report says so (line 13).

**My contact-sheet viewing agrees.** Pages 1-3 show the continuation rows indented. Page 4 shows three rows flush left ending `+200001`. The sentinel is below on every page, and I see no red marker.

**Binary separation.** Bundled `…/dependencies/bin/override/soffice` 26.8.0.0.alpha0 is recorded with its command and profile (`bundled-run.json:2-3`) and kept apart from the UI run. For the bundled binary, only page 4 was viewed and nothing is claimed for pages 1-3 (report line 9). The bundled PDF is hashed but not measured (`verify_alignment.py:29`).

**Limits are disclosed.** The report and plan state:
- the annotation is authoritative and two representations are being carried (plan lines 26-30; report lines 3, 17);
- there is no leading-relation case and no INT fix;
- the result is not a generic serializer;
- any future generator would need guards on grammar, structure and correspondence.

## Findings (P3, informational)

**P3-1 — "The annotation is authoritative" is inferred, not tested.**
- It is consistent with the result: `alignl` exists only in the annotation, and it takes effect.
- But no test supplied a *deliberately divergent* annotation, for example a different constant in the annotation than in the presentation MathML.
- That is the test that would measure the dual-representation risk: does Writer silently show the annotation over conflicting MathML?

**P3-2 — Writer's regenerated MathML was not inspected.**
- After save, Writer writes MathML generated from the StarMath. The verifier checks only the annotations of the saved ODT.
- Whether Writer's own MathML output encodes the left alignment is unknown. It matters for any consumer that reads the MathML instead of the annotation, or for a later export to DOCX, which the report correctly does not claim (line 7).

**P3-3 — The reopen tests Writer's own format, not a second import.** The reopen reads the saved annotation (line 7 says so). This proves the edit persists in Writer's format; it is not a second MathML-only import. This is already disclosed and is not a defect.

## Safe next boundary (optional, still scratch)

- **Divergence probe:** an annotation that deliberately conflicts with the presentation MathML (P3-1), to measure the authority risk before any generator design.
- **Inspect Writer's regenerated MathML** for Object 4 in `align-writer-edited.odt` (P3-2).

Keep everything else unchanged: no generator, no adapter rule, no normalized MathML/OMML edit, no leading-relation or INT work under this spike. No corpus rerun is needed, because production is unchanged.

**Status:** scratch only. EXP alignment is shown narrowly for one hand-authored annotation. The corpus stays `needs_review`, accepted 0, FULL_END_ONLY unsupported, safety skips unchanged.
