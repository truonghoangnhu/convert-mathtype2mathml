# Writer growth at calibrated paragraphs and page boundaries

Status: **three interactive Writer edit/save/close/reopen trials now complete; layout remains needs_review.** Scratch-only experiments; no production change, commit, push or acceptance promotion. Work folder: `work/dsmt4-layout-boundaries-2026-11-08/`.

The new UI inputs are full-context copies of the previous native-flow Writer sample. Target is the first equation in original paragraph8, with191twips before that paragraph and103twips before the answer paragraph. Unlike the prior tall Writer trial at Câu2 answer B, this target is inside the calibrated paragraph. `prepare_samples.py` creates pristine `tall-calibrated.docx`, `forced-wrap.docx` and `page-edge.docx`. The last adds one empty exact560pt QA spacer immediately before the target. This deliberately positions the question near the bottom of page1; it is not a proposed production line-height change.

## Render diagnostics before interactive editing

`render_diagnostics.py` creates separate files under `pre-ui-diagnostics/`. Tall cases use the previously UI-created Word fraction inside the first equation. Long cases append known numeric terms. They are deterministic OOXML probes, **not UI edits/save/reopen evidence**. Installed Writer renders them in isolated profiles; PDFs, page1/2 images, logs, bounding boxes and summary are retained. Relevant PNGs were visually inspected.

| Probe | Observed render | Interpretation |
| --- | --- | --- |
| Tall at calibrated paragraph8 | Whole fraction and surrounding prose visible; Câu1 text yMin169.058pt, answerA199.008pt | Word-serialized replacement fits; separate Writer-authored UI trial below |
| Six added10digit terms | Original heading/prose on one line, whole formula on next line, following prose on a third line | Object moves intact to a new line when it fits the page width |
| Nine added10digit terms | Formula extends past right edge; last term and closing fence not visible | Actual render failure for an equation wider than the page; not a general line-wrap pass |
| Tall near bottom | Full formula visible on page1, answers on page2 | No observed clipping, but question/answer grouping changes; needs_review |

Baseline edge Câu1 text yMin721.058pt, answerA742.558pt, both page1. After the tall edit probe the question text yMin is729.058pt on page1 and answerA26.858pt on page2. These are text bounds, not equation baselines.

## Controlled checks

Removing only the first equation's outer `m:box` from the overwide probe yields a pixel-identical first page; the last term remains absent from PDF text. This rejects removal of that wrapper as a fix for this Writer overflow. Evidence: `pre-ui-diagnostics/overflow-no-box/result.json`. It does not establish every possible cause or renderer behavior.

A separate `w:keepNext=true` control only on the edge question paragraph keeps the whole question and answers together on page2 (question text yMin35.306526pt, answerA65.258pt). It avoids the split by moving the question, with a large blank space on page1. This is a layout tradeoff in the controlled sample, not a source-position-preserving fix or a new converter policy. Evidence: `pre-ui-diagnostics/edge-tall-keepnext/`.

## Interactive Writer trials completed after review

The previous lock-blocked attempts were followed by three actual UI trials. Commands was verified as the first Câu1 `(u_n)` before mutation, selected by Command+Home, Shift+F4 and Return. The original answerA mistaken selection was not edited. Commands received text via paste; each file was saved in DOCX format, closed and reopened in Writer.

| File | Actual UI edit and reopened observation | Evidence |
| --- | --- | --- |
| `tall-calibrated.docx` | Added `1/(1+x²)` inside the first fence at original paragraph8. Full fraction and following answer row visible without observed overlap/clipping. | `tall-calibrated-ui-reopened.png` |
| `forced-wrap.docx` | Added six10digit terms inside the first fence. Formula moves intact to its own line; closing fence, following prose and answers visible. | `forced-wrap-ui-reopened.png` |
| `page-edge.docx` | Added the same fraction after the synthetic spacer. Full formula visible at page1 bottom; all four answers visible at page2 top. Grouping remains needs_review. | `page-edge-ui-reopened-bottom.png`, `page-edge-ui-reopened-answers.png` |

Writer crashed during the initial long-expression save attempt and exposed recovery; that attempt was not counted as a successful save. After recovery, the on-disk forced-wrap file was reopened and Commands was confirmed as the original `(u_n)` before the successful retry. The retry used separate render observation, exit-edit observation, save and reopen steps and succeeded. The cause of the crash has not been established; it is not attributed to the converter.

`verify_ui_roundtrips.py` confirms115 maths in each saved file, unchanged joined prose, only math1 changed in joined math text, one fraction in tall/edge and zero in wrap. It binds math1 to paragraph8 (edge9 because of the spacer), verifies the Câu1 and answer paragraph identities, and checks before191/103twips. These checks supplement the UI screenshots, not full-document semantic acceptance.

**Serialization finding:** the original first equation has one outer `m:box`; all three Writer UI exports remove it. The later all-equation inventory finds110 outer boxes in the baseline and0 in each UI-saved file. The four deterministic headless save/reopen cases likewise go110→0. This is file-wide removal within these samples, not only a change to the edited math. Evidence: `all-math-box-inventory.json`. Thus the observed local content survives after Writer normalization, but preservation of the original production wrapper is not established and must not be asserted. No wrapper was restored after the UI save. No fixed-height frame, keepNext or new converter policy was adopted.

The edge spacer deliberately changes preceding context; this is a pagination experiment, not a measurement of source calibration at page boundaries. Screenshots are local observations rather than a full-document layout pass.

## Headless save then reopen

`headless_roundtrip.py` saves each of the4 diagnostic DOCX files using Writer's DOCX export filter, lets that process exit, then opens the saved file with a fresh process/profile and renders it. Joined prose and the targeted equation text/fraction checks pass; these alone are not a semantic or layout acceptance gate. Target render regions were inspected again after reopening:

- Tall formula remains complete at the calibrated paragraph; measured Câu1/answerA text positions remain169.058/199.008pt.
- Six-term expression remains intact on the next line; measured heading/formula/answerA positions remain160.608/175.308/211.708pt.
- The nine-term overwide expression still loses its final term and closing fence beyond the page. Saving does not fix the visible failure.
- Near the page bottom, the question remains on page1 and answers on page2. Saving does not fix grouping.

The page images are not byte-identical after export, so no pixel equality claim is made for the roundtrips. `before-after-measurements.json` records stable selected text bounds. The earlier no-box comparison is a separate, genuinely pixel-identical A/B result. Headless roundtrips are explicitly recorded as **UI_edit_status=not_run**, not a substitute for the separate interactive trials.

## Word open-only boundary comparison after review

Word UI opened the four existing deterministic probes without formula edits or saving. Screenshots are in the work folder and summarized in `word-open-observations.json`.

| Probe | Word observation |
| --- | --- |
| Six terms with outer box | Formula moves intact to the next line; final term1790123445 and closing fence visible. |
| Nine terms with outer box | Formula exceeds page edge; final term and closing fence clipped. |
| Same nine terms without outer box | Formula breaks at operators across two lines; final term2123456778 and closing fence visible. |
| Edge tall replacement | Whole fraction and all four answers fit at page1 bottom; Câu2 starts page2. |

This closes the missing **open-only Word comparison** in the review's P2-3. It does not supply a Word edit/save/reopen for these larger probes or numeric spacing residuals. The page-edge result differs from Writer (which splits questions/answers). The deterministic edge input still has the Word-serialized run-property confound described in P2-2; the independent Writer UI trial is separately reported above.

The no-box control now has different outcomes by application: it permits operator wrapping in Word, but leaves Writer clipping unchanged. This is evidence against removing the wrapper globally. A future policy needs a real-width source case, break intent and cross-application consequences; no converter change was made. `word-edge-tall-opened.png` captured a repeated Câu1 in partII during search and is not target evidence; the correct target screenshot is `word-edge-tall-target-opened.png`.

## Rendering the UI-saved Writer files

A fresh isolated headless Writer process rendered each UI-saved file to PDF, without mutating its DOCX. All three renders have4pages; transient UI status counts were not used as pagination evidence. Selected regions of page1 and edge page2 were visually inspected. Text-bound measurements match the deterministic diagnostics at the cited labels:

| UI-saved file | Câu1 text yMin | Formula-line yMin | First answerA yMin |
| --- | --- | --- | --- |
| Tall calibrated |169.058 on page1|same composite line|199.008 on page1|
| Six terms |160.608 on page1|175.308 on page1|211.708 on page1|
| Edge tall |729.058 on page1|same composite line|26.858 on page2|

These are pdftotext text bounds, not equation baselines. `ui-saved-render/summary.json` and PDFs/PNGs preserve the measurements. No cross-app spacing residual is inferred from this.

The three actual UI-saved Writer files were also opened in Word without further edits/saving. Word shows the fraction and answers intact for tall; the six-term expression now breaks at an operator across two lines (unlike the boxed deterministic probe); the edge question and answers both fit page1. Screenshots `word-writer-ui-{tall,wrap,edge}-opened.png`. This confirms a local layout difference after Writer export, not full-document or roundtrip acceptance.

## Provenance limits

The three disposable UI input files were intentionally edited in place. No pre-edit package hashes were kept; original source, deterministic builder, and pre-UI diagnostic inputs remain preserved, but package-byte provenance of the UI inputs is incomplete. Their post-edit hashes and target-text checks do not retroactively replace that evidence. The “UI observed” fields in the verifier are explicitly manual observation metadata, not a script assertion of UI activity.

## Review scope

Claude resumed the existing read-only session successfully after the announced credit reset. The completed snapshot review is `docs/working/claude_dsmt4_writer_boundaries_review_2026-11-08.md`; it found no P1 and three P2 evidence gaps. Its “UI not_run” statements describe the earlier snapshot and are superseded only for these three trials by the evidence above. The original review remains unchanged.

Codex's response is `docs/working/codex_dsmt4_writer_boundaries_review_resolution_2026-11-08.md`. No production change is justified yet. Corpus remains `needs_review`, accepted promotions0, FULL_END_ONLY unsupported and original safety skips unchanged.
