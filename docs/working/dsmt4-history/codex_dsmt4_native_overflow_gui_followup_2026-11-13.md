# DSMT4 — native overflow search and real page-end GUI follow-up (2026-11-13)

Continued directly in Codex, scratch only. No production changes, source edits, font/settings installation, commit/push or accepted promotion. Earlier artifacts were preserved. New evidence: `work/dsmt4-codex-native-overflow-20261113/`.

## Outcome

- A bounded search across24 native-rendered pages in four additional full-exam snapshots did not yield a clean standalone formula overflowing the page body horizontally. No new W/L candidate was manufactured by narrowing columns or changing margins.
- The real page-end L case from the preceding report now has an actual GUI edit/save/close/reopen result: Object333 remains editable with two rows on page7.
- A fresh `SAL_USE_VCLPLUGIN=osx` headless export of the exact GUI-saved ODT matches the actual GUI PDF on all7 pages and all12,296 glyph records.
- Retain the earlier conclusion: W is preferable for this short price equation; L moves the entire paragraph to page7 and does not solve a width problem.

## Bounded horizontal-overflow search

Starting inputs are the existing Nov6 native-OMML DOCX snapshots under `out/dsmt4-writer-comparison-2026-11-06/patched/`. Each was imported to a new ODT, then exported to PDF from that ODT. Every conversion used a distinct fresh profile and the system LibreOffice with `SAL_USE_VCLPLUGIN=osx` plus `--headless`.

| Exam | PDF pages | Line-bound outliers | Review classification |
|---|---:|---:|---|
| Toan_TQB_HN_Lx | 4 | 3 | Three first-page heading/title lines extending past the body right margin; not formula candidates |
| Hoa_Bac-Ninh_L1 | 11 | 26 | Prose lines around the Phe/Ni illustrations on pages3,5,8,11; left edge5.4428pt outside the global body margin; not a clean standalone formula-width case |
| Hoa_Ha_Noi_L1 | 5 | 0 | No outlier in this measurement |
| LI-12-So-GD-Bac-Ninh-25-26 | 4 | 0 | No outlier in this measurement |

Method: use the single explicit ODF page layout's page width and left/right margins, ignoring default-style properties without page geometry. Flag extracted PDF text lines more than2pt outside those horizontal body bounds. Recompute every recorded candidate from its PDF in `verify_inventory.py`.

The three TQB outliers stay inside the physical page; their excess beyond the body right margin is approximately11.05–33.36pt. The26 chemistry outliers are left-side prose-region flags; their right edges remain inside the body. Some flagged prose lines include small inline equations, but the measured left-edge flag is not evidence that a standalone equation is too wide.

Visual review covered the TQB heading page and all four flagged chemistry pages, recorded in `TQB-header-review-1.png`, `Chem-margin-review-03.png` and `Chem-flags-contact.png`. No eligible new W/L target was selected from these29 flags.

**Limits:** this is a global body-bound PDF-text scan. It does not establish absence of overlap or overflow within cells, columns, floating text regions, images, or non-text formulas. The snapshots are existing converted artifacts, not a new fidelity-certified conversion of the current source set. Known unrelated rendering/content issues are not accepted by this search. Physics ¶91 and all safety/unsupported policies remain unchanged.

## GUI follow-up of the proven real page-end case

Input: `work/dsmt4-codex-real-pageend-20261113/price-L-odt/price-L.odt`. Provenance remains image338.wmf / oleObject333.bin, Tuyên Quang descendant paragraph215 (zero-based), as recorded in the preceding page-end review. Its original mathematical result is8,5.

Actual CUA sequence:

1. Finder → Open With → LibreOffice opened that saved L ODT.
2. View → Navigator selected Object333; Return selected the OLE frame; Return entered Math.
3. Commands displayed `matrix{ { p = 7 + 0,25 ( 6 ) } ## { { } = 8,5 } }`.
4. Selected only `8,5`, typed `8,6` as a deliberate editability probe, then Save As created new `pageend-L-gui-edited.odt` in this new scratch directory.
5. Closed the test document, reopened that new absolute path through Recent Documents, and re-entered Object333 in Math. Commands retained the same matrix ending in8,6.
6. Writer's Export Directly as PDF created `pageend-L-gui-reopened.pdf`; the test document was closed afterward. The older align-writer-edited document stayed open and untouched. Other user documents were not edited or closed.

The8,6 file is an intentionally altered diagnostic artifact, not the original exam or a mathematically corrected result. Original W/L files remain unchanged.

Artifact verification confirms:

- Seven PDF pages; Object333's two rows and leading second-row equals remain together on page7.
- The actual PDF contains `p=7+0,25(6)` and `=8,6`; the following Câu6 heading remains below the formula without overlap or a target error marker.
- All355 Math annotations were compared: only Object333 has the deliberate numeric delta; the other354 match the original saved L input.
- All body paragraph plain-text strings match before/after save.
- Six pre-existing error markers remain elsewhere in the complete PDF; this is not whole-exam acceptance.

The enlarged GUI target was visually reviewed in `GUI-target-detail-7.png`. Exact UI observations and pins are in `gui-verification.json`.

## Same-file native/GUI check and review

A new system headless process exported `pageend-L-gui-edited.odt` using `SAL_USE_VCLPLUGIN=osx` and a new profile. Its PDF and the actual reopened GUI PDF match across all7 pages and12,296 glyph records, comparing character, effective font name, size and x0/top/x1/bottom rounded to5 decimal places. This new pair was not compared as full-page rasters; no new raster-equivalence claim is made.

The executable remains `/Applications/LibreOffice.app/Contents/MacOS/soffice`, `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77`, with the same executable hash pinned by the earlier font/layout study. No bundled alpha was used. No shell command controlled the GUI; all GUI operations used CUA. The headless commands retained `--headless` with the per-process VCL override.

Review disposition:

- **Closed within this case:** the previously untested Object333 GUI edit/save/reopen step, and a same-file native headless/GUI glyph comparison after that edit.
- **Unchanged:** W keeps the short original price equation at the end of page6; L moves the paragraph as a unit to page7. Automatic splitting is still unjustified for this case.
- **Still open:** an actual horizontal-overflow formula suitable for W/L testing; region-level cell/column overflow checks; INT semantic handling; full-exam source fidelity. The negative global-bound search does not close those items.

## Verification

- `inventory.py`, `inventory-runs.json`, `inventory-pins.json`, `overflow-candidates.json`: eight conversions, four source snapshots,24 pages and29 outliers. Resume guards verify and reuse already-created outputs instead of overwriting them.
- `verify_gui.py`, `gui-verification.json`: actual GUI evidence plus saved MathML/Commands and exported-PDF checks.
- `check_native_reopen.py`, `native-reopen-comparison.json`: exact native headless command, fresh profile, output pins and glyph comparison.
- `verify_inventory.py`: fresh source/output hash checks, candidate remeasurement, executable/version pin, previous page-end/acceptance pins and independent same-file glyph comparison.

Verification passed within the stated scope. Previous source/sidecar/manifest/acceptance pins and all four new snapshot input pins remain unchanged. No commit/push or accepted increment.
