# DSMT4 linebox isolation — 2026-11-07

Status: **diagnostic only; corpus remains needs_review**. No production rule or acceptance promotion results from this experiment.

## Controlled Writer comparison

The sample contains only source Toán paragraphs 8–9 (Câu 1 stem and choices), using the original package assets, styles and section properties. A second sample contains the corresponding current native OMML paragraphs. Two counterfactual source samples remove object-run `w:position`, or change only the seven VML picture heights to 12pt respectively. All four were rendered through fresh isolated Writer profiles.

| Variant | Câu text yMin (pt) | Choice text yMin (pt) | Stem-to-choice gap (pt) |
| --- | ---: | ---: | ---: |
| Source | 36.858 | 58.358 | 21.50 |
| Current candidate | 27.308 | 43.658 | 16.35 |
| Source without object-run position | 36.858 | 58.358 | 21.50 |
| Source pictures forced to 12pt high | 28.158 | 43.258 | 15.10 |

These are text bounding-box positions, **not measured formula baselines or complete paragraph line boxes**. Removing object-run position yields pixel-identical Writer images in this sample. Changing picture height accounts for 8.70pt of the 9.55pt first-stem text displacement, but visibly squashes formula glyphs. That counterfactual is not a conversion repair. It also does not reproduce the original stem-to-choice gap. This two-paragraph result cannot be generalized to all source equations or document pagination.

## Word observation

A separate comparison DOCX contains the same four pairs of paragraphs, with a label before each pair. Word displayed all groups on one page. In Word, removing object-run position visibly raises OLE formula glyphs relative to adjacent prose; the source group remains aligned. The 12pt-height variant visibly compresses the formula glyphs. The native candidate is editable math with different glyph metrics and a visibly tighter stem-to-choice gap.

Unlike Writer, Word therefore responds to object-run positioning in this sample. A common rule that transfers picture lowering into native math is not supported by these observations. No quantitative Word PDF measurements or edit/save/reopen checks were performed for this diagnostic DOCX; this is a direct UI rendering observation only. The small-margins print confirmation left over from an earlier test was canceled; no PDF export is claimed here.

## Evidence and verification

### Follow-up: noBreak wrapper isolated

At 22:xx local, a further controlled Writer probe removed only the seven outer `m:box/m:noBreak` wrappers from the extracted candidate. Their `m:e` children were inserted in place, preserving the ordered `m:t` strings. Source and candidate paragraph properties already match structurally: stem uses automatic single spacing, choices use automatic 1.15 spacing with the same tabs and indent. The wrapper-removal output is pixel-identical to the current candidate render, with all five label x/y positions unchanged. This excludes the wrapper as the source of the measured geometry difference **in this sample**, and gives no reason to remove its wrapping protection in production. Script: `probe_box.py`; evidence: `box-result.json` and `candidate-no-box/`. That diagnostic output intentionally lacks protection and is not a migration candidate. No Word render or roundtrip was performed for wrapper removal.

All new artifacts are under `work/dsmt4-linebox-isolation-2026-11-07/`: `probe.py`, `height_only.py`, four extracted DOCX files, their Writer PDFs/PNGs/bounding boxes, `comparison.png`, `label-metrics.json`, `word-linebox-comparison.docx`, and `word-comparison.png`.

`verify_probe.py` independently rereads the saved bounding boxes, reproduces the label metrics, checks pixel equality for position removal in Writer, and checks all eight Word-comparison paragraph structures against their corresponding extracted DOCX bodies. Following Claude's P3 feedback, it also verifies all 42 image/OLE relationship references: unique internal relationship, existing target part, matching relationship type, effective content type, and SHA-256 against the respective variant package. It passed. This verifies artifact construction and measured facts, not formula acceptance.

The next production investigation must separate native-math ascent/descent, source preview dimensions, and paragraph layout in each application, then validate any narrow proposed rule against both applications and whole documents. The earlier paragraph-wide height-floor probe remains rejected. Current production tests were not rerun for these scratch-only diagnostics; the recorded 118 Java / 144 Python results apply to their earlier snapshot.

After the usage reset, the same Claude session completed the outstanding confirmation and closed the reproduction P3. Claude also reviewed the linebox report and verification script read-only, finding no P1/P2 or numerical interpretation error. The two new P3 items (asset resolution checks and stale review-status prose) were addressed by Codex; the updated verification script passed with 42 references. Claude did not run commands, inspect the PNGs, or perform UI checks, and has not re-reviewed these small follow-up changes. Original response: [Claude linebox review](./claude_dsmt4_linebox_review_2026-11-07.md). The later noBreak diagnostic script is Codex-only evidence. No commit, push, merge, PR change, original-data change, or old-output overwrite was made. FULL_END_ONLY and the original safety skips remain unchanged.
