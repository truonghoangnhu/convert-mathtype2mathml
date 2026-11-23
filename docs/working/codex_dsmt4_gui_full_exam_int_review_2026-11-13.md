# DSMT4 — Codex direct continuation: GUI, full exam and INT (2026-11-13)

Continued directly in Codex after the Fable same-session dispatch hit its quota. Scratch evidence only. No production change, commit, push, corpus promotion or accepted increment. The prior rev2 review remains separate: its two P2 and one P3 were closed within that earlier scratch scope.

## Outcome

| Track | Observed result | Acceptance boundary |
|---|---|---|
| Writer GUI | Scalar, fraction and long Object3, and full-exam Object309, each opened in Math, edited, saved under a new name, closed, reopened, re-entered in Math, then exported through the Writer GUI | Three synthetic documents plus one target edit in the full exam; whole-exam fidelity remains open |
| Full exam | A genuine long sidecar works as one row W and as two rows L in a complete existing exam snapshot after removing the target's stale preview | L changes page flow; W already fits. No automatic split or full-exam acceptance |
| INT | Direct source locator and read-only Equation Native decode confirm the first integral's main slot contains only `|`; polynomial and closing bar follow as outer siblings | Binding evidence, not proof of mathematical equivalence; no regrouping or acceptance |

System executable: `/Applications/LibreOffice.app/Contents/MacOS/soffice`, `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77`. Every new headless conversion used a separate fresh profile. The bundled alpha was not used. GUI actions used CUA only; shell commands did not control GUI applications. Another open scratch document was left untouched.

## GUI evidence and review

Artifacts: `work/dsmt4-codex-gui-roundtrip-20261113/`.

Actual interaction is recorded in `observations.json`; `verify_gui.py` rechecks saved artifacts and exported PDFs. Only Object3 was individually entered and edited in each document:

- Scalar: `2,5` → `2,6`.
- Fraction: denominator `10` → `11`.
- Long: `(6−n)` → `(7−n)`.

Reopened Math Commands retained each deliberate edit and the empty-left operand before the second-row `=`. Saved MathML has two rows and two equals signs; the fraction retains two fraction nodes. Object1/2 annotations match their original expected Commands, but those objects did not receive individual GUI activation. Original input hashes still match the earlier handoffs.

All nine exported pages were rendered and visually inspected. Positive Object3 pages retain the leading relation without a new red marker or placeholder. The raw negative controls still show their known relation error. This establishes the bounded GUI edit/save/reopen result; it does not establish source semantics or whole-exam fidelity.

## Full-exam route and findings

Artifacts: `work/dsmt4-codex-full-exam-20261113/`; the reviewable pair is **`uncached/`**. Earlier attempts are retained as diagnostics, not passing outputs.

Starting snapshot: `out/dsmt4-writer-comparison-2026-11-06/patched/Toan-So-GD-Tuyen-Quang-lan-1-omml.docx`. This is an existing Nov6 native-OMML snapshot, not a new run of the current converter. It was imported by the system Writer into a new ODT.

The long source locator is descendant paragraph index188 (zero-based), image314.wmf/rId627, oleObject309.bin/rId628. The existing manifest maps that preview part to sidecar `929091afb048ddf147590ac574ad428044c63f37a9cb7d9f5f4a507298e21bf1.wmf.mathml`. This reuses established sidecar provenance; there is no new source-semantic certification of this long equation.

The unique matching imported formula is `Object 309/content.xml`, in the paragraph prefixed “Mặt khác:”. W and L reuse the prepared sidecars from the previous phase3. L is a deliberate split before the second equality, not automatic line wrapping. Neither branch contains the GUI edit to `(7−n)`; both retain source-side `(6−n)`.

The two input ZIPs differ from each other in **only the target MathML part**. Relative to the imported ODT, each branch changes exactly four parts: target MathML; body XML removing only the target draw:image and svg width/height; the manifest removing only that preview entry; and removal of the corresponding replacement binary. All other package parts are byte-identical. Anchor and paragraph/frame styles are retained. The verifier compares the body XML canonically against precisely those allowed edits.

### Stale-preview trap — resolved for this scratch pair

Keeping the old replacement binary produced a misleading result: the saved MathML/Commands had two rows, while PDF displayed the old single-row preview stretched to the new taller frame. Removing the draw:image reference alone was insufficient. The original and both misleading saved replacement binaries all hashed to `a0ac62d125bf37faf8c361411438104c1df7d89d5840507d149b2e55c28517d9`.

The uncached pair removes the binary and its manifest entry as well. The saved ODTs retain no old target replacement image. A fresh-profile PDF export from each saved ODT now renders the actual target equation: W has equals signs at the same height; L has a 17.165pt separation between them. Visual inspection confirms two rows, a visible leading `=`, and no target error marker. This is why XML counts or successful save alone would have produced a false pass in the earlier attempts.

### Layout result — remains open

Both outputs have seven pages. The target is on page6. The saved frame is approximately 244.86×16.30pt for W and 156.36×31.86pt for L. The measured paragraph ink box includes the prose prefix; it is not a formula-frame height estimate.

At 90dpi, pages1–5 are pixel-identical between W and L. Page6/7 differ: L moves the final “Tính…” integral paragraph from page6 to page7 and shifts following content. The non-target extracted character sequence matches after excluding exactly the target paragraph and each terminal page footer. Both full documents retain six pre-existing `¿` glyphs elsewhere; this pair is not a clean whole-exam conversion.

L also vertically centers the prose prefix between its two formula rows, and Writer centers the shorter first math row. These require layout review if this form is pursued. The one-row W formula already fits the actual page, so this case provides no reason to split it automatically.

Visuals: `uncached/candidate-L-target-6.png` and `uncached/affected-pages-contact.png`. PDFs and saved ODTs are under the corresponding `baseline-W-*` and `candidate-L-*` directories.

## Full-exam GUI roundtrip — editability observed, layout divergence remains

The uncached saved candidate was opened through Finder → Open With → LibreOffice. Navigator selected Object309; Return selected its OLE frame and a second Return entered Math. Commands showed the expected two-row matrix. Only `( 6 - n )` was selected and replaced by `( 7 - n )`. Save As created `work/dsmt4-codex-full-exam-20261113/full-exam-L-gui-edited.odt`; the document was closed, reopened through Recent Documents, and Object309 was entered again in Math. Commands still contained the two-row matrix and `( 7 - n )`. Writer's Export Directly as PDF created `full-exam-L-gui-reopened.pdf`. The test document was then closed; the older align-writer-edited document remained open.

`verify_gui_full.py` verifies the original uncached input is unchanged, all355 Math annotations are present, only Object309's annotation changed by the intended constant, and the reopened GUI PDF has seven pages with the edited two-row formula and visible leading equals on page6. The target has no error marker; six pre-existing markers remain elsewhere. All224 body paragraph plain-text strings match before/after the GUI save. Other formulas did not receive individual GUI Math editing.

**The GUI PDF does not reproduce the headless page flow.** Its page6 starts near the “Kẻ AH…” paragraph instead of the earlier PartII/III content; page7 starts with the end of Câu5 instead of the integral calculation. All seven GUI pages were rendered and visually reviewed, including enlarged pages6/7. Thus the bounded target edit/save/reopen check passes, while full-exam layout acceptance remains open.

`pdffonts` confirms different embedded font sets despite the same application version: headless includes Liberation Serif and Linux Libertine G variants; GUI includes TimesNewRomanPS variants, Liberation Serif, Menlo-Italic, AppleSymbols and HiraMinProN-W3. This is direct font-set evidence; font substitution's causal contribution to the reflow has not been isolated with a controlled baseline. Neither run should stand in for the other. Shell FONTCONFIG environment variables were absent when checked.

GUI save adds z-index attributes to the formula frames; only Object309 changes width/height (and its frame style/baseline offset). The non-target frame dimensions remain the same. PDF extracted character multisets also differ beyond the intentional edit, so no claim of complete PDF content equivalence is made; unchanged body text and other Math annotations alone do not resolve that discrepancy.

Evidence: `gui-full-verification.json`, `gui-full-layout-review.json`, `gui-full-first-five-contact.png`, `gui-full-page-6.png`, `gui-full-page-7.png`. The PDF and ODT are review artifacts with a deliberate mathematical edit, not deliverables for use as the original exam.

## INT source binding and decoder hazard

Artifacts: `work/dsmt4-codex-int-source-20261113/`. `audit.py` reproduces the source locator, byte comparison and decoded slot checks; `records.rb` independently reads Equation Native with `Ole::Storage.open(..., 'rb')`.

Direct `word/document.xml` and relationships locate descendant paragraph151 (zero-based, conventionally ¶152), object index2, OLE rId446/oleObject218.bin and preview rId445/image223.wmf in the **same w:object**. No formula was reconstructed from the preview.

The current DOCX BIN and staged BIN differ as compound-file bytes, but their 794-byte Equation Native payloads match exactly, SHA256 `f3992c03bcabb4481ee06facb87115e73c2e1f86e848ea6f7590741382187007`. Decoded MTEF XML also matches.

- First `tmINTEG`: main slot contains U+007C only; lower slot0, upper slot2; operator U+222B. Polynomial terms and the closing U+007C are subsequent siblings in the outer slot.
- Second and third integrals have the parenthesized polynomial in their main slots, with bounds0/1 and1/2.
- Local `xsl/transform/int.xsl` explicitly maps first slot to main content, second/third to bounds and fourth to operator. This establishes the decoder/transform interpretation, not mathematical intent.
- The sidecar has the same boundary shape: first mstyle contains msubsup plus bare bar; polynomial and closing bar are outer math siblings. Thus there is no evidence here that the sidecar transform dropped the polynomial from that first slot.

The embedded TeX Input Language comment is retained as source metadata only. It is not executable slot binding or an independent mathematical oracle. The earlier bare-bar → `mline` import problem remains distinct. No cross-slot absolute-value reconstruction, K-rule expansion or source repair was attempted.

### Parser opens input for writing — new review finding

`tools/calabash/extensions/transpect/mathtype-extension/ruby/mathtype-0.0.7.5/lib/file_parser/ole.rb:10` opens OLE with **`rb+`**. Reproduction on a disposable copy changes its container hash from `0c520b9782ff8aeb4a87519a8baf2b4f77304cf8966ce508046e664819413f17` to `d0bcc065fc70c79cc3bb880315a037cbd338b49731cece8bcd4dae5c8b6aac98` on parser close, while Equation Native stays the same. The resulting hash matches the staged BIN.

The initial source-copy artifact `current-input-ole218.bin` was affected by this behavior; it must not be described as pristine. The reproducible audit now retains a separate pristine ZIP extraction, runs the legacy converter only on a temporary disposable copy, and uses an independent `rb` read for the payload/record check. It rechecks the pristine hash afterward. The current DOCX hash remains `4d33c222a87ba9af2ef526dd29070575fd9971cfa841e403c500d92600fbec14`; the staged BIN still matches its initial `source-pin.json`. Production parser code is unchanged.

Some nested BinData offsets/lengths are null because non-writable metadata primitives prevent their calculation. Those fields are not raw-byte offset proofs; the independent whole Equation Native byte equality is the applicable evidence.

## Verification and remaining work

Fresh checks completed:

- `work/dsmt4-codex-gui-roundtrip-20261113/verify_gui.py`.
- `work/dsmt4-codex-full-exam-20261113/verify.py` and `verify_gui_full.py`, plus `measure.py` and `review_pixels.py`.
- `work/dsmt4-codex-int-source-20261113/audit.py`, using disposable legacy-parser input and independent read-only decode.
- Earlier phase2 and phase3 input pins (5 and7 respectively), initial staged BIN pin, and current source DOCX pin remain unchanged.

Next bounded work: isolate the GUI/headless font and PDF-text discrepancy with a controlled whole-document baseline; select an actual overflowing/page-end formula before designing an automatic split policy; investigate a source-safe delimiter representation for INT without crossing MTEF slot boundaries. Any parser hardening belongs to a separately authorized production change. No change to FULL_END_ONLY support, safety skips, Physics ¶91, or accepted status is implied by this review.
