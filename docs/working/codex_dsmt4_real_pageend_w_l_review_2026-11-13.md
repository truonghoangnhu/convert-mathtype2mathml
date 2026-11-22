# DSMT4 — genuine page-end equation W/L review (2026-11-13)

Scratch-only continuation directly in Codex. No commit/push, production changes, source changes or accepted promotion. New artifacts: `work/dsmt4-codex-real-pageend-20261113/`.

## Selected case and natural page-end evidence

Selected **`p = 7 + 0,25(6) = 8,5`**, in the paragraph “Giá thuê tối ưu là … (triệu đồng).” of the Tuyên Quang exam. This is a short real equation near the end of a page, not a horizontal-overflow case.

Direct source locator in `in/Toan-So-GD-Tuyen-Quang-lan-1.docx`: descendant paragraph215 (zero-based; ¶216), first object, preview image338.wmf/rId675 and OLE oleObject333.bin/rId676 in the same w:object. The existing manifest maps image338.wmf to genuine sidecar `fec9c71b125bfb51e7e352ff970e02b103b8b24ef55298d5fa165fe4b874b4af.wmf.mathml`. No preview reconstruction or BIN decoding was performed. This reuses sidecar provenance; it is not a new source-semantic certification.

Whole-document context: existing Nov6 patched native-OMML snapshot imported to ODT in the earlier experiment. The unique formula is `Object 333/content.xml`. This experiment starts from that original imported ODT; the earlier Object309 W/L changes and `(7−n)` GUI edit are not present.

A new native render of the original context confirms the price paragraph is the **last body line on page6**. Its ink bottom is789.09276pt and footer text begins at808.09276pt: a19pt ink-to-ink gap. W retains exactly those vertical positions. This gap is an observable distance to footer text, not a computed body-frame limit or a claim that19pt is available for extra content.

No spacer, inserted page break, page size, margins, paragraph style or footer changes were used to create this condition.

## Controlled W/L pair

Both branches use `/Applications/LibreOffice.app/Contents/MacOS/soffice`, version `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77`, with **`SAL_USE_VCLPLUGIN=osx`** and `--headless`. Original-context PDF, W/L saves, and PDF exports from the saved ODTs each use a distinct fresh profile.

- W: the genuine sidecar receives the existing W wrapper.
- L: manually split before root child8, the second equality. The existing L preparation inserts the empty left operand before the second-row equals. This is a diagnostic manual split, not automatic wrapping.
- Ordered original element subtrees match between W and L after excluding only that inserted empty operand. No formula tokens are invented or edited.

The input ZIPs differ from each other in **only Object333 MathML**. Relative to the imported context, both make the same target-only cache invalidation and size reset: target MathML replacement, removal of the target draw:image and svg dimensions in body XML, removal of its cached replacement binary, and removal of that entry in the manifest. Page styles and inherited Math settings stay byte-identical. No obsolete target preview remains in either saved branch.

## Observed result

| Measure | Original context | W | L |
|---|---|---|---|
| Document pages | 7 | 7 | 7 |
| Price paragraph page | 6 | 6 | 7 |
| Formula rows | 1 | 1 | 2 |
| Formula ink top/bottom, pt | 777.08076 /789.09276 | 777.08076 /789.09276 | 35.58076 /62.84276 |
| Next body line on same page | None | None | Câu6 heading |
| Target error/placeholder markers | 0 | 0 | 0 |

Saved Commands:

```text
W: { p = 7 + 0,25 ( 6 ) = 8,5 }
L: matrix{ { p = 7 + 0,25 ( 6 ) } ## { { } = 8,5 } }
```

W remains on the last body line of page6, and page7 starts with Câu6 as in the original context. W is not pixel-identical to the original formula: native MathML import changes its glyph spacing slightly, while the page flow remains the same.

L moves the **entire paragraph**, including prose prefix, units and both formula rows, to page7. The first row does not remain on page6. Its leading second-row equals is visible; equals tops differ by15.25pt. Câu6 starts at64.14276pt rather than35.24276pt in W, approximately28.9pt lower. The prefix and units sit vertically between the two formula rows; the shorter second row is centered rather than left-aligned.

All7 pages of each PDF were rendered. The affected pages6/7 were visually compared in `pageend-contact.png`; enlarged `W-end-detail-6.png` and `L-start-detail-7.png` were also inspected. No clipped target glyph, missing leading equals, target error marker or overlap with the Câu6 heading was observed.

W/L pages1–5 are identical in full glyph records and at100dpi pixels. The extracted non-target text sequence matches original/W/L after excluding exactly the price paragraph and terminal page footers. All355 Math annotations were compared after save: only Object333 changes, and354 non-target annotations remain identical. Each full PDF retains six known error markers elsewhere; this is not a clean full-exam acceptance result.

## Review conclusion

This is a genuine natural page-end stress case with a complete exam context. It shows that L can retain the two rows and leading relation after Writer save/fresh reopen for PDF export, but it **does not help fit this paragraph on page6**: the taller inline formula causes the paragraph to move as a unit to page7.

Retain W as the preferable diagnostic layout for this case. There is no evidence supporting an automatic split here. Page count alone would hide the layout change because all three documents remain seven pages. Likewise, `columnalign="left"` in the prepared MathML does not establish left-aligned Writer rows; the actual PDF shows centering.

The current result is headless with the native backend proven comparable to GUI in the preceding same-file study. No new individual GUI edit/save/reopen test was performed for Object333, and no claim of GUI acceptance or general page-break behavior for all equations follows from this case. INT semantics, full-exam source fidelity and automatic split policy remain open.

## Verification and artifacts

- `prepare_case.py`, `plan.json`, `pins-before.json`: source locator, sidecar mapping, original context and allowed package changes.
- `run.py`, `runs.json`: exact binary/version, per-process native override, five fresh profiles, input/output hashes and conversion logs.
- `measure.py`, `measurements.json`: unique target detection, formula-only glyph boxes, original-context page-end observation, non-target text and page/pixel comparisons.
- `verify.py`: source/acceptance pins, allowed XML changes, unchanged page styles/settings, one-part W/L difference, saved Commands,354 unchanged other annotations, absence of stale target cache, target pagination and first-five-page pixel equality.
- `price-W-odt/price-W.odt`, `price-L-odt/price-L.odt`: saved review artifacts.
- `price-W-pdf/price-W.pdf`, `price-L-pdf/price-L.pdf`: PDFs exported from those saved ODTs.

Fresh verification passed within the stated scope. Source DOCX, original snapshot/imported ODT, genuine sidecar, manifest, preparation script and both acceptance/corpus documents retain their starting hashes. No accepted increment, commit or push.
