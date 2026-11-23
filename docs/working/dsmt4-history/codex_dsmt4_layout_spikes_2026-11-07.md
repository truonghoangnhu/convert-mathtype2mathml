# DSMT4 layout experiments after linebox isolation

Status: **prototype only, needs_review**. No production code, source, fixture, prior output, Git publication or acceptance ledger was changed. Artifacts are in `work/dsmt4-line-alignment-probe-2026-11-07/`.

## Paragraph line-height experiment

On the extracted Toán Câu1 stem/choices, Writer stem-to-choice text yMin gaps were source21.50pt, native16.35pt, bottom-aligned15.85pt, exact source-height×original-auto-multiplier21.10pt, exact+bottom21.20pt, and minimum-height21.70pt. Word UI PDF measurements on a shared comparison page gave source19.44pt, native13.92pt and exact/minimum21.12pt. These measure text boxes, not equation baselines.

A full-context minimum-height probe modifies35 converted inline paragraphs and excludes5 display paragraphs. Ordered heading binding was verified. Changed-page headings decreased4→2, but10/16 comparable local gaps still differ by more than2pt, with both under- and overcompensation. This is not a production fix. Exact line heights also lack proof against clipping after tall edits. Scripts: `probe.py`, `probe_minimum.py`, `full_context.py`; results and fresh PDFs/PNGs are alongside them.

The distinction between fixed/minimum line height and character vertical alignment follows [line-spacing semantics](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.spacingbetweenlines.line?view=openxml-3.0.1) and [text alignment semantics](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.textalignment?view=openxml-3.0.1). Renderer behavior was checked rather than inferred from those definitions.

## Native frame experiment: rejected for editing

A transparent VML inline textbox retains source height and object-run positioning, containing the unchanged native equation. Original source widths clip native glyphs in both Word UI and Writer render. Native widths are different from preview widths; for example the second expression measures103pt in Word versus85pt in its source frame. Expanding widths using the actual Word PDF restores content but initially wraps choiceD in Writer. Inspection of Writer's saved ODT traces the extra space to outer frame margins of0.1252in (~9pt) on each side. Explicit zero wrap distances removes that extra margin.

The resulting v4 sample restores Writer Câu1/A–D label x/y positions exactly and displays all7 expressions. Word UI displays all7 and its same-PDF stem-to-choice gap error improves4.80→0.96pt. This does not prove matching prose x positions: expanded frame widths add horizontal whitespace in Writer. The widths are calibrated to this sample, not generally computed by the converter.

**The v4 frame fails the required edit contract.** Codex used Word UI to append `+1` inside the first native equation, saved, closed and reopened. Saved XML contains `u`, `n`, `+1`, but the reopened rendering hides the added text outside the fixed frame. Word's Resize-shape-to-fit-text and disabling Wrap-text-in-shape were also tried through the document UI: the displayed controls changed, but the saved VML still retains24pt width without the corresponding fit settings, and reopening still hides `+1`. No claim is made about a universal Word limitation; this is the tested compatibility-mode sample. Evidence: `word-growth-verification.json`, `word-growth-reopened.png`, `word-growth-autofit-reopened.png`, and `word-edit-growth-qa.docx`.

VML auto-fit/no-wrap variants do not resolve clipping in Writer. A hand-built modern DrawingML alternative also fails Writer rendering (overlapping formulas) and is rejected. Do not infer production suitability from its schema shape or numeric label positions. No Writer UI edit trial was completed for these rejected frames. `writer-edit-growth-qa.docx` is an untouched QA copy, not evidence of an edit pass.

Failed construction attempts `native-frame-fit-width.docx` and `native-modern-frame-v5.docx` are incomplete diagnostic ZIPs, not candidates. Valid subsequent versions have explicit v2/v6 suffixes. All frame artifacts remain scratch only.

## Promising direction: measured spacing before single-line paragraphs

A separate experiment keeps ordinary native OMML in document flow and changes only `w:spacing/@w:before`. It neither constrains line height nor adds a textbox. This avoids the fixed-container clipping mechanism, but interactive growth still must be tested on this new sample.

For Writer, only full-context Toán paragraphs8/9 change, by191/103twips (9.55/5.15pt). Fresh render yields source-identical Câu1/A–D label x/y: heading(43.75,161.058), choiceA(57.9,182.558), and B–D at their original tab stops on the same row. The7 equation trees are byte-identical to the current candidate. Stem prose boxes differ only by vertical translation; rendered visible stem text is unchanged. Small sub-point math metrics and PDF word grouping differ, so exact glyph-box equality is not claimed. `verify_before_sample.py` passed and writes `writer-before-sample-verified-v2.json`. It explicitly binds the actual `Câu 1.` heading, replacing an initial incorrect instruction-reference match in `writer-before-sample-result.json`.

For Word, a separate paired source/native/calibrated comparison uses178/96twips before the two native paragraphs. The first value accounts for inherited6pt space after the comparison label. Word UI PDF measurements give source/native/calibrated heading-to-label gaps21.752/18.872/21.992pt, and stem-to-choice gaps19.44/13.92/18.72pt. Thus residual errors are+0.24/−0.72pt in this sample. This is an application/context calibration, not one set of values proven for both applications. Source gap measurements also vary slightly among comparison documents; a sub-point exact-match claim would be unwarranted.

Artifacts: `spacing_before_probe.py`, `verify_before_sample.py`, `Toan-writer-before-sample.docx`, `writer-before-sample/`, `word-before-comparison.docx`, its actual Word-produced PDF, and `word-before-measurement.json`. The full-exam output only changes these2 paragraphs; it is not a full-exam layout repair.

## Before requesting a fix review

The earlier Claude review debt is closed. No new Claude review was launched for these experiments: there is not yet a production-ready layout rule. Next work is to verify edit/save/reopen with longer and taller native formulas on the spacing-before sample, implement a reproducible renderer-based measurement/binding process rather than hardcoded paragraph numbers, and establish guards for single/multiline paragraphs, inherited/collapsed spacing, page-top suppression and changed wrapping. Then validate larger full-context samples in both applications and send the narrow proposal, red/green checks and render/roundtrip evidence to the same Claude session. Fixed frames and blanket paragraph floors must not be promoted as shortcuts.

No Java/Python production tests were rerun for scratch-only changes. `git diff --check` is the repository whitespace check for this batch. Accepted promotions remain0; FULL_END_ONLY and all original safety skips remain unchanged.
