# DSMT4 growth/boundary scratch batch review (2026-11-11)

**Scope:** I reviewed only the narrow scratch batch, read-only, with Read/Glob/Grep. I did not edit, execute or render anything. This is not a production or corpus audit.

**Verdict:** No P1 or P2 issues. The report's claims match the rendered evidence I viewed. There are five P3 limitations in the verifier and the evidence chain, all minor. The corpus status is unchanged: `needs_review`, accepted 0, FULL_END_ONLY still unsupported, safety skips and Lý ¶91 unchanged.

## Required scope statements (confirmed)

- **Case A, fraction:** the nested fraction was built by the script before any UI step. `build_probes.py:22-27` builds `(5+2t)/((t+1)/(t+2))`. The only UI edit was changing the first numerator from 5 to 6, in Word and in Writer (report lines 9, 17, 19; `plan.json:22`). This tests whether a tall structure that already exists survives an edit and a save/close/reopen. It does not test inserting a fraction through the UI, and it does not measure growth before and after the same edit.
- **Cases B and C:** they had no interactive edits of their own. They went through the same document-level save/close/reopen as A (report line 19; `plan.json:22`).
- **Case B, long equation:**
  - **Word** wraps the 24-term sum automatically into 3 lines: …13t, then +14t…22t, then +23t+24t. AFTER_B stays below (`long-comparison.png`, first panel).
  - **Writer** renders a single line that runs past the right page edge. A partial "17" glyph is the last visible ink, so terms 17/18 to 24 are not on the page (`writer-growth-reopened-page-2.png`). The saved DOCX still contains all 24 terms in order (`verification.json:29`), so XML checks cannot catch this failure. Report lines 3 and 31 are accurate.
- **Explicit-lines workaround:**
  - **Writer:** after save and reopen, all 24 terms render as 3 rows (…8t / +9t…16t / +17t…24t), with AFTER_B below (`writer-explicit-lines-reopened-page-2.png`).
  - **Word view:** shows the same 3 rows, within the margins (`explicit-lines-word-view-page-2.png`). The saved XML has an `m:eqArr` with 3 `m:e` (`verification.json:43`).
  - **Alignment:** in both apps the rows are centred relative to each other (row 1 is indented), so align-left is not preserved.
  - **Limits:** this is a manual rewrite of one known addition pattern. It does not prove a generic break-insertion rule for normalized MathML or for the Word converter, and it does not prove align-left (report lines 35, 39).
- **Case C, page end:**
  - **Pages 3 and 4:** in both apps, page 3 holds only the "GROWTH C" label and PAGE_END_SPACER. The whole three-row system moves to page 4, with AFTER_C directly below it (Word and Writer page-3/page-4 images).
  - **What this is not:** this tests a case where there is not enough room at the bottom of the page. It is not an exact-fit test at the boundary and not a system taller than a page. The label is separated from its system (report line 13).

## Findings

**P1:** none.

**P2:** none.

**P3-1 — Page-end check rests on one token.** `verify_and_render.py:51`
- The page number used to be hardcoded. It is now taken from a PDF token containing "x" on page 3 or later, and `verification.json:53,62,71,80` reports page 4. That fix is confirmed (report line 45).
- However, the script finds only the `x` row. It does not assert that the `y` and `z` rows are on page 4. It also does not record the page of the "GROWTH C" label, so "label stays on page 3" is supported only by viewing the images.
- **Fix:** also locate the y/z tokens and the "GROWTH C" word, and assert label = page 3 and all rows = page 4.

**P3-2 — Fragile anchor; only vertical edges checked.** `verify_and_render.py:28,45`
- The ROI top is anchored to the exact word `system` on page 1. It is unique today only because AFTER_A's word is `system.` with a full stop.
- The edge-touch assert at line 45 checks only the top and bottom edges, not left and right. Writer places the brace almost on the left edge of the ROI (`writer-growth-reopened-tall-ink.png`).
- The 600 dpi crops confirm the current numbers are sound: the Writer brace is one stroke of about 78pt, and the Word brace about 60pt. Both crops have clear space above and below.

**P3-3 — `long-comparison.png` cannot show the page edge.** `verify_and_render.py:50`
- Each panel is a fixed pixel crop, `(60,70,w-30,260)` at 130 dpi.
- The right edge of the crop is about 433pt, which is inside the 450pt page. In the Writer panel, the overflow therefore ends at the crop boundary, not at the page edge.
- The full page-2 render is what shows the off-page clipping. Cite that file, not only the comparison image, as the evidence for "Writer clips".

**P3-4 — Cross-view copy is only partly verified.** `verify_and_render.py:22`; `cross-view.json:1-4`
- `cross-view.json` stores only the hash of `explicit-lines-word-view.docx` before the Word view. That proves Word did not save over the file.
- It does not prove the file is a byte copy of `writer-explicit-lines-ui.docx`: no source hash is recorded, and the XML checks at lines 15-21 do not include it. "Bản sao" (copy) in report line 37 is therefore asserted, not verified.

**P3-5 — Some visible differences are not stated.** These do not contradict any claim, but a wider conclusion should not skip them:
- Word centres the A and C systems; Writer places them at the left margin with a thin, tall brace (pages 1 and 4).
- The ink heights compare different renderers, not growth. Word reads 60.12pt for the file Word saved and 58.56pt for the Writer-saved file viewed in Word; Writer reads 78.00pt. Report line 29 already says these are raster ink extents, so they should not be read as growth or used for layout fitting.
- In the Word view of the explicit-lines file, rows 2 and 3 start with a tightly spaced "+9t" / "+17t", while row 1 has spaced binary operators. This is cosmetic.
- In Word on page 1, the gap between the z row and AFTER_A is very small, but nothing overlaps.

## Inspected

- **Report:** `docs/working/codex_dsmt4_growth_boundaries_2026-11-11.md`, lines 1-47 (current version, including the addendum at lines 45-47).
- **Batch files:** `build_probes.py`, `verify_and_render.py` (current version, line 51 uses the "x" token lookup), `plan.json`, `verification.json`, `cross-view.json`.
- **Images, as requested:**
  - `long-comparison.png`;
  - `word-growth-reopened-page-1/3/4.png`;
  - `writer-growth-reopened-page-1/3/4.png`;
  - `writer-explicit-lines-reopened-page-2.png`;
  - `explicit-lines-word-view-page-2.png`.
- **Extra images:** `writer-growth-reopened-page-2.png`, `writer-growth-reopened-tall-ink.png`, `word-growth-reopened-tall-ink.png`.

## Not inspected

- The DOCX/ZIP XML directly; I relied on the script plus `verification.json`.
- The PDFs and their `pdftotext` output. The fonts in the report (Georgia 11 for prose, inherited math run properties) are not verified.
- Other images and pages:
  - `word-growth-reopened-page-2.png` as a full page (seen only through the comparison crop);
  - explicit-lines and cross-view pages 1, 3 and 4;
  - `explicit-all-pages.png`;
  - `*-tall-ink.png` for the explicit-lines files.
- Other files in the batch: `saved-structure.json`, `explicit-lines-input.json`, `final-checks.json`, `checkpoint.json`, `claude-*.json`.
- The UI sessions themselves. I did not infer UI behaviour from XML, and I did not re-run any script.
- The prior UI batch (`work/dsmt4-height-ui-2026-11-11`), the line-metrics batch, the old corpus and production code.

**Status:** this is scratch evidence only. There is no acceptance promotion and accepted remains 0.
