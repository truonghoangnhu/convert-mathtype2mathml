# Native equation growth on the spacing-before prototype

Status: **4 local UI growth checks and4 expanded cross-application save/reopen checks completed. Claude review blocked by weekly credit limit.** This is a scratch experiment, not a production layout policy or corpus acceptance. No commit or push was made.

## Word

Two separate QA copies use the calibrated native-flow sample with paragraph spacing-before of178/96twips. Through Word UI, Codex changed the first equation, saved, closed the document, and reopened it:

- Long: `(u_n + 1234567890)` remains visibly complete inside the equation. Evidence: `work/dsmt4-growth-roundtrip-2026-11-07/word-long-math-reopened.png` and `word-long.docx`.
- Tall: adding a professional fraction `1/(1+x²)` grows the line naturally; the fraction remains visible without observed clipping or overlap after reopening. Evidence: `word-tall-reopened.png` and `word-tall.docx` in the same folder.

Saved XML independently confirms the added content is inside the first `m:oMath`, with one `m:f` in the tall case, and that178/96twips spacing survives. `verify_growth.py` reproduces the limited XML checks; the current result is `saved-xml-verification-final-2026-11-08.json`. The earlier `saved-xml-verification-2026-11-08.json` is the initial checkpoint before the Writer trials. This supplements the observed UI result and is not an acceptance test by itself.

The initial `word-long-reopened.png` shows a discarded attempt that appended text outside the equation. It is **not valid evidence** of a math edit. Only the corrected `word-long-math-reopened.png` supports the long case. New Word-entered characters used the editor's11pt default; this batch does not establish font/style carry-over for newly typed characters.

## Writer

`writer-long.docx` and `writer-tall.docx` began as full-context copies of `Toan-writer-before-sample.docx`, with191/103twips before the two Câu1 paragraphs. After the user exited Full Screen and opened the first formula, Codex completed two actual UI edit/save/close/reopen trials, keeping DOCX format at the Writer format prompt:

- Long: append `+1234567890` inside the first `(u_n)` formula. The added digits remain visible inside the growing formula after reopening. Screenshot: `writer-long-reopened.png`.
- Tall: add `1/(1+x²)` to the first row of the **Câu2 answer B system, math occurrence14**. All three rows, the fraction and the following Câu3 remain visible without observed clipping or overlap after reopening. Screenshot: `writer-tall-reopened.png`. This is a different target from Word's tall trial and lies outside the two calibrated Câu1 paragraphs. It proves local system growth in document flow; it does **not** prove tall editing on Writer's calibrated first paragraph.

The targeted formulas change as intended. Joined non-math text and joined text of all other formulas remain equal to the input; formula count remains115. Writer splits many math runs, so raw run-list equality would give false differences. These checks do not establish whole-document semantic, formatting or pagination equivalence.191/103twips survives the saves.

The earlier automation problems were selection errors, not conversion failures. An accidental unsaved edit was discarded. Coordinate actions still sometimes report `AXError.notImplemented`; unknown object accessibility indices can select a different formula. Actual target commands and saved XML were inspected instead of trusting the requested object index. The Mac has multiple installations sharing LibreOffice's bundle identifier; use `/Applications/LibreOffice.app` explicitly. Use paste for StarMath commands to preserve Unicode minus and avoid typed auto-bracket insertion.

## Expanded cross-application trials

Separate copies in `cross-app-2026-11-08/` went through the other application:

| Input edited in | Re-saved and reopened in | Target observed after reopen |
| --- | --- | --- |
| Word, long | Writer | Full added number visible |
| Word, tall | Writer | Full fraction and surrounding text visible |
| Writer, long | Word | Full added number visible in full-exam context |
| Writer, tall system | Word | Three-row system and added fraction visible |

Each cross copy received a reversible prose `q`/Backspace edit to force a real save, then was closed and reopened. Package changes were confirmed; simply pressing Save on an unchanged Word document initially left the bytes unchanged and was not counted as serialization. Joined prose is unchanged in all4 copies; targeted text/fraction checks pass. Screenshots and `verification.json` are alongside the copies. Cross-application trials are save/reopen checks, **not4 additional formula edits**. No full-document layout or semantic pass is claimed.

**Correction to the initial cross-app finding:** the raw text of math78 changes from Unicode `ℝ` to `R`, but Word also writes `m:scr m:val="double-struck"`. Word UI directly displays the expected blackboard-bold real-number symbol after reopening; screenshot `cross-app-2026-11-08/writer-long-word-double-struck-R.png`. The earlier commentary and `review-evidence-2026-11-08.json` incorrectly called this plain-R content loss. That conclusion is withdrawn; `review-evidence-corrected-2026-11-08.json` supersedes it. Other raw differences include mathematical minus/ASCII minus and prime/apostrophe encodings; they are diagnostic deltas, not automatically accepted or failed formulas. Neither raw `m:t` equality nor mismatch alone is sufficient to judge rendering or semantics.

## Claude review

The first read-only attempt was blocked by the weekly limit. After reset, the same session completed the review: `docs/working/dsmt4-history/claude_dsmt4_writer_boundaries_review_2026-11-08.md`. It accepts withdrawing the premature plain-R-loss claim and records remaining cross-app/layout evidence gaps. The raw first attempt remains retained as historical evidence.

## Gate for further work

The local growth milestone and narrow cross-application expansion are complete. The subsequent three Writer UI trials at the calibrated Câu1 paragraph, forced wrapping and page edge are recorded in `codex_dsmt4_writer_boundaries_2026-11-08.md`. The strengthened verifier binds Word's178/96 spacing directly to target paragraph2 and answer paragraph3; `saved-xml-verification-paragraph-bound-2026-11-08.json` supplements the earlier immutable result. Word sample generation provenance and a common spacing rule across applications remain unestablished.

The application-specific constants remain prototypes. Corpus remains `needs_review`, accepted promotions0. FULL_END_ONLY and original safety skips are unchanged. No production code changed or production suite was rerun for these scratch experiments.
