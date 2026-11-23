# Shared Word and Writer spacing experiments

**Status: experiment complete, no production layout rule adopted; needs_review, accepted promotions0.** Scratch folder: `work/dsmt4-layout-shared-spacing-2026-11-09/`. No source, ZIP, fixture, prior output, commit or push changed. These are the same two extracted Toán Câu1 paragraphs repeated in controlled contexts, not an expanded corpus acceptance audit.

## Reference correction after Claude review

Claude found a P2 interpretation issue: the source OLE previews sit high relative to prose in Writer but align with prose in Word. This matches the earlier position-removal isolation (Writer ignored the source picture lowering). Thus “0.00” against Writer's source is a match to that renderer's OLE behavior, **not fidelity to the intended Word DOCX layout**. The Writer-source residuals below remain diagnostic data, not optimization targets. Word's rendering of the source is now selected as the primary DOCX layout reference; this choice does not prove the authoring application or universal rendering correctness.

The follow-up `codex_dsmt4_shared_spacing_resolution_2026-11-09.md` records the proposed58/103 panel and compares both native renderers with the Word-source label distances. The original comparison remains preserved.

## Reproducible comparison

`build_matrix_v2.py` creates `spacing-matrix-v2.docx` and `page-top-matrix-v2.docx` from the preserved source/candidate isolation documents. It retains the7 native math trees per native panel and verifies source embedded relationships point at identical bytes. V2 assigns unique shape/ObjectIDs to copied source OLEs. The first construction reused IDs within a paragraph; its artifacts are retained but superseded by v2. All16 rendered page images and all measurements are pixel-identical between initial and v2 in their respective applications (`v2-verification.json`); v2 is the review input.

Each of four contextual pages contains source OLE, unchanged native OMML, before178/96twips, and before191/103twips. Contexts are preceding label after0, label after6pt, contextualSpacing on question/answers, and before spacing inherited from explicit unique paragraph styles. The separate top matrix puts each source/native configuration at a page start using pageBreakBefore for subsequent pages; no keepNext is added. This controls a manual page break, not every kind of automatic pagination.

Word itself exported PDFs via its Print→PDF UI. Writer rendered the same DOCX files using fresh isolated installed-app profiles. Both produce4pages per file. PDFs were converted to PNGs; all contextual pages and the target regions of all top pages were inspected. The Word margin warning was confirmed only for these QA PDFs. There is no printer submission. DOCX hashes match the manifest after Word viewing/export.

The marker immediately before each question binds label, Câu1 and first answerA; ambiguous instruction references cannot match. `compare_measurements_v2.py` requires all16panels. Values below are **PDF text bounding-box differences in points**, not equation baselines or semantic acceptance.

## Same values across applications

Residuals below are native minus source, in each renderer's own paired comparison. “Heading” means marker-to-Câu1 distance error; “choice gap” means Câu1-to-first-A distance error.

| Context | Values before stem/choices | Writer heading | Writer choice gap | Word heading | Word choice gap |
| --- | --- | ---: | ---: | ---: | ---: |
| After0 |178/96|−0.65|−0.35|+6.00|−0.72|
| After0 |191/103|0.00|0.00|+6.72|−0.24|
| After6pt |178/96|−6.65|−0.35|0.00|−0.72|
| After6pt |191/103|−6.00|0.00|+0.72|−0.24|
| Contextual spacing |178/96|−9.55|−5.15|−2.88|−5.52|
| Contextual spacing |191/103|−9.55|−5.15|−2.88|−5.28|
| From style |178/96|−0.65|−0.35|+6.00|−0.72|
| From style |191/103|0.00|0.00|+6.72|−0.24|

Without any compensation, after0 heading/choice-gap deficits are9.55/5.15pt in Writer and2.88/5.28pt in Word. These are diagnostic comparisons to each app’s own source rendering, including the Writer OLE distortion. The previously proposed question spacing was renderer/context dependent: preceding after6pt masks6pt of the added before spacing under this document’s compatibility settings. Contextual spacing suppresses the intended compensation here because the preceding label and the question use the same paragraph style. A one-level style supplying the entire spacing element renders like the corresponding direct value in this controlled test; partial attribute inheritance is untested; that does not authorize overwriting an existing style or its inherited spacing.

At a page start, the question yMin is27.308pt in Writer for all three native configurations and27.228pt in Word for all three. The source yMin is36.858/30.108pt respectively. Thus the added before value does not move the question at the tested page starts; it leaves a9.55/2.88pt native-source difference. The answer gap changes, but cannot fix the initial question position by itself. Source is at the first document page; native variants use explicit pageBreakBefore. Automatic page-top suppression and alternative compatibility settings are not separately isolated here.

**Decision:** reject these constants as a shared automatic layout fix. The measurements explain why a local exact Writer sample and a different local Word sample did not establish one DOCX rule. Do not remove contextualSpacing, existing style spacing or page breaks to force the compensation. A renderer-specific measured output remains an experiment, not a converter feature.

## Larger Word UI edit and reopen

Two new full-exam scratch copies preserve their pre-edit hashes in `growth-inputs.json`:

- `word-boxed-growth.docx`: six numeric terms inside the existing box. Added `+1` inside the delimiter using Word UI, saved, closed and reopened. All terms, added1 and closing fence remain visible on one formula line, following prose and answers below. Outer box stays1.
- `word-unboxed-growth.docx`: nine-term no-box control. Added `+1` inside the delimiter, saved, closed and reopened. It remains complete across two lines, including final2123456778+1 and closing fence. Outer box stays0.

`growth-verification.json` confirms115maths/file, unchanged joined prose and the targeted math text equals the input plus `+1` inside the delimiter. Other raw math-text normalization deltas from Word saving are listed and are not treated as semantic acceptance. Initial caret attempts landed before the last digit or in prose; these were undone. The successful final files are checked for exact target text and unchanged prose rather than counting those attempts as passes.

Screenshots `word-boxed-growth-reopened.png` and `word-unboxed-growth-reopened.png` show the final reopened state. These close two larger local Word edit cases, not the nine-term boxed overflow (still a known synthetic failure), a full document fidelity pass, or cross-app symbol acceptance. Previous Writer no-box evidence still shows clipping; no global removal of the box follows from the Word control.

## Limits and handoff

No general spacing fix is ready. The guard/context evidence is now measured in both applications on identical DOCX inputs, with build/version metadata in `v2-verification.json`. Full-context generalization, automatic page breaks, true baseline measurement and reverse cross-app symbols remain open. Tall/page-edge Writer edit evidence from the preceding batch remains separate and unchanged. FULL_END_ONLY unsupported; safety skips and Lý¶91 retained; corpus needs_review.

The same Claude session receives a read-only review of the v2 builder, measurement binding, the negative conclusion and the two Word UI cases. No production test suite is rerun for scratch-only experiments; targeted verifiers and `git diff --check` are the relevant checks for this batch.
