# Shared spacing review response and smaller compensation trial

The read-only Claude review found no P1 or builder/verifier defects. Its P2 concerns the reference target: Writer renders the source OLE images too high relative to prose. Codex verified that visual difference in the paired source panels and the earlier position-isolation evidence. The report now labels Writer-source residuals as renderer diagnostics and uses Word's source render as the primary DOCX reference. This is a stated reference choice, not a claim about the original authoring application.

## Suggested58/103 trial

`build_matrix_v3.py` adds58/103twips as one additional panel in every context and one additional manual page-top case. All other variants remain. `spacing-matrix-v3.docx` has4pages; `page-top-matrix-v3.docx` has5pages, in both apps. Word exported actual PDFs through its UI; Writer rendered fresh isolated profiles. Native math trees were copied unchanged, source identifiers are unique, and DOCX hashes match the pre-UI manifest. The target render regions on all pages were inspected.

`primary-Word-reference-v3.json` compares the same prose label distances to the source rendered by Word. These are text bounds, not baselines. Each pair below is [marker-to-Câu1 error, Câu1-to-first-A error], in pt.

| Context | Word58/103 vs Word source | Writer58/103 vs Word source | Writer58/103 change from its native baseline |
| --- | --- | --- | --- |
| Previous after0 |0.00, −0.48|+0.55, +2.06|+2.90, +5.15|
| Previous after6pt |−2.88, −0.48|−2.35, +2.06|0.00, +5.15|
| Same-style contextualSpacing |−2.88, −5.52|−2.35, −3.09|0.00, 0.00|
| One-level style spacing |0.00, −0.48|+0.55, +2.06|+2.90, +5.15|

The smaller value repairs the heading distance locally in Word under after0; Writer's corresponding heading distance is about0.55pt below the selected Word source reference. The choices remain about2.06pt farther apart in Writer than in the selected Word reference. This is not a common exact layout fix, and no acceptance tolerance has been imposed.

At the manually broken page top,58twips does not move the question in either app. Word yMin27.228 remains2.88pt above its source30.108; Writer yMin27.308 is2.80pt above the Word source. Choice gaps are18.96pt (Word) and21.50pt (Writer), versus19.44pt in the Word source. Automatic page breaks remain untested. Source occupies the first document page; native variants occupy later pages after pageBreakBefore.

## Interpretation and scope

The after0 heading result is promising for a **Word-reference, measured local sample**, not for hardcoded converter constants. The after6/contextual/page-top counterexamples remain. No existing after/style/contextual/page-break property was removed to make compensation work. The one-level style case does not test partial inheritance where a paragraph overrides some spacing attributes. Word residual changes around0.24pt are quantization/noise and must not be called exact improvements.

The two larger Word UI formula edits remain successful local content/edit observations, with their new+1 inside the delimiter and unchanged prose. They do not validate the new58/103 panel interactively, cross-app semantic fidelity, or boxed overwide growth. There is no global no-box change.

## Review artifacts

- New v3 matrices, builder, manifest and extracted text bounds remain in the scratch folder. `comparison-v3.json` keeps per-app source diagnostics; `primary-Word-reference-v3.json` is authoritative for the revised interpretation.
- The renderer/extraction helper stores yMin of the first word in a matched line, not a baseline. Its code is supplied in the follow-up review, closing the previous extraction-review omission if independently confirmed.
- The initial duplicate-ID construction is superseded by v2/v3; the inputs and outputs remain retained. V2 image equality and v3 content/ID/hash verifiers document the construction.

No production code changed, no corpus re-audit, accepted promotions0, corpus needs_review. FULL_END_ONLY unsupported, original safety skips and Lý¶91 retained. No commit/push/merge/PR change.

## Claude follow-up completed

The same session reviewed v3 and closed the reference-interpretation P2. Report: `claude_dsmt4_shared_spacing_followup_2026-11-09.md`. It found no verifier error; its remaining P3 asked for a saved generator of the primary-reference JSON. Codex added `derive_primary_reference_v3.py` and ran it: all4rows/24residual components reproduce the existing JSON exactly. That small generator has not received another independent review.

The review also clarifies that Word's0.24pt step size limits interpretation of tiny residuals. The58/103 choice-gap result should be described as approximately−0.5pt, not exact glyph placement. The AFTER6 comparison supports previous-after + measured deficit under this document's spacing collapse, while contextual/page-top cases remain excluded. These facts do not establish constants for other formulas.

The next justified experiment is a **measurement-only full-context Word-source/native comparison**, binding each question/answer row and recording prior-after/style/contextual/page-start and compatibility flags. Apply no compensation during that measurement. If deficits vary with equation height, a per-paragraph metric model is needed; the current two-paragraph sample cannot justify generalizing58/103.
