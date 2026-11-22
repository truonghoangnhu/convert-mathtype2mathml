# DSMT4 pre-review closeout — 2026-11-07

Status: **needs_review**, accepted promotions **0**. This completes the new pre-review verification batch, not overall DSMT4 acceptance. Claude independent review is scheduled after 01:35 local time and has not yet run. No commit/push/merge or source/ZIP/fixture/previous-output writes.

## Interactive editing

Six standalone Math/ODF samples were edited through UI, saved under separate names, closed and reopened, with resulting formulas visually checked:

| Occurrence | Actual edit | Result after reopen |
| --- | --- | --- |
| toan078 | a → b | `(b ∈ ℝ)` retains ℝ |
| tn020 | B → D | absolute-value bars, subscript and ℓ retained |
| hoa023 | X → Q | `Q²⁺,Y²⁺,Y³⁺` retains charges |
| toan046 | 2,7 → 2,8 | `[2,8;3,0)` retains asymmetric delimiters |
| toan015 | first-row constant 2 → 3 | all three rows retained and left aligned |
| toan011, new V candidate | first coordinate 5 → 6 | vector accent and `(6;2;−3)` retained |

An additional **Writer embedded Math/ODT** test edited toan069 from `(91;75;0)` to `(92;75;0)`, saved a separate two-object QA ODT, closed and reopened. Both vectors remained visible. This is neither original full-exam UI editing nor DOCX roundtrip acceptance. Saved commands, artifact hashes and routes are in `work/dsmt4-acceptance-closeout-2026-11-07/ui-verification.json`.

The initial raw XML renamed `.odf` opened as text in Writer; it is not counted. Actual tests used packaged formula documents with the formula MIME type and prepared MathML content.

## New content failure and bounded repair

The existing prepared toan011 imported into Math as ordinary `u=(5;2;−3)`: its vector accent was lost although the formula had no parse-error marker. Three scratch glyph/stretch variants did not restore it. Therefore the earlier 36-case check establishes absence of its historical **parse/fence** symptoms only; it does not prove complete formula content. A fresh check exposed a new dimension that marker scans miss.

The installed build's [matching MathML importer source](https://raw.githubusercontent.com/LibreOffice/core/bce0998afefdbc355585ca324285661a2170ba77/starmath/source/mathml/mathmlimport.cxx), `SmXMLOverContext_Impl::HandleAccent`, constructs an attribute node with `TACUTE` and an empty math character. Runtime loss was independently observed. The separate Math adapter now adds **V**, a generated StarMath annotation for only a complete unstyled assignment of one ASCII-letter vector to exactly three signed integer coordinates in parentheses. It preserves the prepared presentation subtree, including the original mover/arrow; it does not change normalized MathML or Word OMML.

The command is constrained from the complete parsed formula, never inferred from preview or fingerprint. Decimal/symbolic coordinates, other accents/arrows, multi-letter vector names, foreign/metadata input, mixed text, styling and other tuple lengths receive no V annotation. Existing metadata inputs remain byte-identical. The rule is not a general mover converter.

Regression failed before the repair (`V` absent) and passes afterwards, with rejection cases. **143 Python tests pass**. Java/Word sources did not change in this batch; prior 116 Java and gate4/4 are not described as fresh reruns here.

Fresh Math outputs: `out/dsmt4-vector-followup-2026-11-07/`. Only **toan011 and toan069** change among 265 candidates; **263 byte-identical** to the previous Math snapshot. Prepared presentation trees of both changed candidates remain identical inside their new semantics wrapper. Both were rendered, saved in ODT and rendered after reopening; `vec u` annotations and mover nodes persist, and reopened render was viewed. The two new UI tests above cover standalone Math and Writer embedding separately.

## Whole-exam layout

All five original sources and current Word-targeted candidates were freshly rendered with **Writer headless**, and all page contact sheets visually compared. This is current Writer rendering evidence, **not fresh Word rendering or UI saves**.

| Exam | Source / candidate pages | Finding |
| --- | --- | --- |
| Lý Nghệ An | 5 / 5 | Vertical reflow remains |
| Công nghệ | 4 / 4 | Every page pixel-identical; no DSMT4 in this exam |
| Toán TQB | 4 / 4 | Major reflow; questions10/11 move to page1 and much less content remains on page4 |
| TN-THPT | 4 / 4 | Final-section lead-in moves across pages3/4 |
| Hóa Hà Nội | 5 / 5 | Text/diagrams cross different page boundaries |

Equal page counts do not establish placement fidelity. The four migrated exams remain `needs_review` for full layout. These results do not authorize guessed spaces, adjusted content, removal of safety skips or a universal font/spacing change. Existing native OMML and paragraph preservation are structural evidence, not proof of identical rendering metrics. Detailed renders and observations: `work/dsmt4-acceptance-closeout-2026-11-07/layout/visual-review.json`.

## Ledger and review

`work/dsmt4-acceptance-closeout-2026-11-07/current-ledger.json` preserves all **265 occurrence identities**, prior route-scoped evidence and the 247 Word candidates / 18 retained OLE mapping. It points the independent Math route at the fresh V snapshot and attaches only the measured new UI evidence. Accepted promotions remain0; the current full failed total is not established. FULL_END_ONLY and the original safety skips, including Lý paragraph91, remain unchanged.

Claude's task must review the leading-temperature helper from the prior batch, new V parser/annotation safety and tests, actual route distinctions, the vector omission correction and layout limits. The review cannot be marked completed before a result arrives. Outstanding findings should be fixed with appropriate regression/application checks; no PR publication is authorized by this closeout.
