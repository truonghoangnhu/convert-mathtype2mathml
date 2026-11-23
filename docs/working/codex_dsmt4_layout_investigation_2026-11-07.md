# DSMT4 layout investigation after standby — 2026-11-07

Status: **needs_review**. No production code, original data or prior output was changed. This investigation quantifies current Writer reflow and rejects an insufficient spacing repair; it does not complete overall migration acceptance.

## Measured question positions

Using the already fresh source/candidate Writer PDFs of all5 exams, heading anchors are ordered by physical page/y/x and verified against complete ordered `Câu n.` paragraph-heading sequences in source DOCX XML. The first extraction included5 inline references in Lý; those **were not actual question starts**. They are excluded in final v4 using the common heading column only when the resulting complete sequence/count exactly matches XML. Thus the final sample is **134 headings, not139**. Ambiguous bindings are rejected. Each PDF directory must have exactly one PDF.

| Exam | Verified headings | Heading changes page | Comparable local gaps | Local gap changes >2pt |
| --- | ---: | ---: | ---: | ---: |
| Hóa Hà Nội |28|4|19|12|
| Lý Nghệ An |28|0|23|4|
| TN-THPT |28|0|24|2|
| Công nghệ |28|0|24|0|
| Toán TQB |22|4|14|12|

A local gap compares consecutive headings only when both endpoints lie on the same page in both renders. Absolute y shifts are retained only as auxiliary position data, and marked confounded after unmatched page transitions. They are **not counted as independent paragraph-height errors**. Header word and containing text-line yMin/yMax are recorded; a text-line box is not automatically the complete line box of the paragraph or its formula.

Evidence: `work/dsmt4-layout-investigation-2026-11-07/anchor-review-v4.json`. Earlier v1/v2/v3 files remain diagnostic history and are superseded by v4.

## Source-height floor probe: rejected

A separate Toán copy changes automatic paragraph spacing to an at-least floor derived from the largest source OLE preview height. The original candidate remains untouched. This affects all40 paragraphs containing OLE in the source, including5 whose candidate math is display math. No paragraphs in this specific probe were skipped for inherited spacing; the experiment is not a general style resolver.

The probe reduces heading-page changes4→3 and reduces a supplementary global-position displacement metric, but it neither reproduces source placement nor fixes the mechanism. On page1, consecutive-gap differences include −7.55pt, −12.2pt and −19.2pt (still too compressed), while the Câu8→9 gap becomes **+3.5pt** (overcompensated). Visually, Câu11 is split across the new page boundary while its source starts on page2. A paragraph-wide minimum also applies to text-only lines and changes paragraph semantics. **Do not ship this floor.** No Word rendering/editing was tested for it.

Evidence: `height-floor/measurement-v2.json`, `height-comparison.png`, all in the investigation folder. The mean-global-y calculation was exploratory and is not a local-cause or acceptance measure.

## More precise cause trace

Toán source paragraph8's OLE previews are20.7/18.4pt high, with object-run positions−7/−6pt and12pt font size. The source paragraph spacing is automatic. The candidate preserves paragraph properties but replaces preview objects with native math and does not carry picture-specific run positioning. Native-math line geometry therefore warrants investigation; this does **not** justify copying OLE lowering onto formula glyphs.

For Câu1–9 on page1, selected prose-word sequences match in source/candidate, as do their y-level counts. This is evidence against extra prose wrapping as the main cause in those selected words; it is **not a complete physical-line count**, formula-height measurement or proof that width changes elsewhere are harmless. Raw prose/line boxes are stored in `prose-trace.json`, source object/run metrics in `inline-dimensions.json`.

The next useful isolation is source preview ascent/descent and actual math extent on the same line, together with font/math-option rows, followed by equivalent Word evidence before any targeted placement rule. A global font/spacing correction or synthetic padding is not supported by this batch.

Subsequent controlled two-paragraph experiments and a direct Word UI comparison are recorded in [linebox isolation](./codex_dsmt4_linebox_isolation_2026-11-07.md). Writer ignores object-run positioning in that sample (pixel-identical result), whereas Word visibly responds to its removal. Reducing source picture height explains much of the first-stem text displacement in Writer but distorts glyphs; it is not a proposed production fix.

## Independent review

The same Claude Code session reviewed the probe read-only. It found no P1, but raised2P2 measurement/interpretation issues: cumulative drift is not a count of local errors, and changed-page transitions confound absolute y comparisons. Codex addressed them in v4 with comparable consecutive gaps and explicit confounding flags. It also fixed false inline-reference anchors, recorded line boxes, made PDF selection unambiguous and inventoried probe coverage. Original review: `claude_dsmt4_layout_review_2026-11-07.md`. That initial review did not verify final v4 independently. A subsequent read-only review has now checked v4 and closed both P2 findings; see [review-debt resolution](./codex_dsmt4_review_debt_resolution_2026-11-07.md). Claude still did not run commands or observe UI.

No production tests were rerun because the batch changes scratch diagnostics only. Previous118Java/144Python results remain scoped to their recorded snapshot. The existing occurrence ledger, accepted0, FULL_END_ONLY unsupported and original safety skips/Lý paragraph91 stay unchanged. No commit/push/merge/PR change or new automation was made.
