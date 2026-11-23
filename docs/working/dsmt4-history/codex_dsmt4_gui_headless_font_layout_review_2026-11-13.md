# DSMT4 — same-file GUI/headless font and layout review (2026-11-13)

Continued directly in Codex. Scratch only: no production code/configuration change, font installation, GUI preference change, commit, push or accepted promotion. Existing inputs, PDFs and the earlier review were preserved. New evidence is under `work/dsmt4-codex-font-layout-20261113/`.

## Result

The GUI/headless discrepancy is reproducible on the **identical saved full-exam ODT**, and it disappears within the measured scope when the system LibreOffice headless process is launched with `SAL_USE_VCLPLUGIN=osx`.

| Render of the same saved ODT | Pages | Fonts/text relative to GUI | Glyph geometry | Poppler raster relative to GUI |
|---|---:|---|---|---|
| Actual prior GUI reopen/export | 7 | Reference | Reference | Reference |
| Default headless, fresh profile | 7 | Different | Different on all7 pages | Different on all7 pages |
| Headless with `SAL_USE_VCLPLUGIN=osx`, fresh profile | 7 | Same | All12,296 glyphs match | All7 pages pixel-identical at100dpi |
| Minimal headless repeat, only `SAL_USE_VCLPLUGIN=osx`, another fresh profile | 7 | Same | All12,296 glyphs match | No additional raster comparison needed; the primary controlled pair already establishes the raster result |

Glyph comparison includes character, effective embedded font name with subset prefix removed, size, x0/top/x1/bottom rounded to5 decimal places in PDF points. Raster comparison uses the same system Poppler and RGB pixels for both PDFs. This is visual/geometry equivalence for this exact file and environment, not byte-identical PDF files or project acceptance.

The headless flags remain present in every command, including the `osx` runs. No GUI was launched or controlled through a shell command during this investigation. There were no new GUI edits in this session; the reference is the actual prior GUI reopen/export whose source and PDF hashes were rechecked.

## Controlled input and executable

Input: `work/dsmt4-codex-full-exam-20261113/full-exam-L-gui-edited.odt`.

SHA256: `4e4694bd853d48e107c8ae21888fb48ca432e7fa059534a07c5f64c0964e1497`.

GUI reference: `work/dsmt4-codex-full-exam-20261113/full-exam-L-gui-reopened.pdf`, matching the earlier `gui-full-verification.json` hash. The ODT includes the earlier deliberate Object309 edit `(6−n)` → `(7−n)`; it is a diagnostic artifact rather than the original exam.

System binary: `/Applications/LibreOffice.app/Contents/MacOS/soffice`.

Version: `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77`.

Executable SHA256: `820ce37c7f7f496f73516d932109b1254463b33a993ceae0cfbaabac62f164bf`.

Both primary headless runs receive that same input and executable. Each profile was absent before launch and distinct from the GUI profile. Apart from separate output/profile paths, the sole environment variable under test is `SAL_USE_VCLPLUGIN=osx`. `SAL_LOG` and `DYLD_PRINT_LIBRARIES` were identical diagnostic settings in the primary pair. A repeat omitting both diagnostics still matches all GUI glyphs, ruling out dependence on those logging settings.

This removes the earlier save/edit confound: the default headless discrepancy persists even after reading the exact GUI-saved file. Native `osx` selection reproduces the GUI result with a fresh profile, so copying the user's GUI profile is not required for this case.

## Font evidence and interpretation

Default headless embeds Liberation Serif, Linux Libertine G variants and OpenSymbol. The GUI and `osx` headless output embed the same set including TimesNewRomanPS variants, Liberation Serif, Menlo-Italic, AppleSymbols, HiraMinProN-W3 and OpenSymbol. Names and full `pdffonts` outputs are recorded in the artifacts.

Times New Roman is already present under `/System/Library/Fonts/Supplemental/`; no font installation was needed. Default-headless stderr contains Fontconfig cache warnings; the native run does not. The native run emits a macOS task-policy warning but exits0 and produces the verified output.

**Supported causal conclusion:** selecting the VCL `osx` path changes the observed font/render/layout result and is sufficient to reproduce this GUI PDF on the same file. The difference is not explained by an extra Math edit, a different ODT, or a need to reuse the user's GUI profile.

**Limit:** this experiment changes a backend selection, which can affect font discovery, shaping, metrics and rendering together. It does not isolate one font family as the sole cause, prove the exact internal default backend name, or diagnose an upstream LibreOffice defect. No claim of a universal fix for other platforms, binaries or documents is made. PDF character extraction discrepancies from the prior default-headless comparison also vanish for the identical-file native run; this does not certify mathematical source equivalence.

## W/L layout review with the native path

W and L were exported again with `SAL_USE_VCLPLUGIN=osx` from the earlier **uncached** input ODT pair. Those two input ZIPs differ in only `Object 309/content.xml`; both retain `(6−n)`. No GUI-save delta or changed cached preview is introduced between them.

Both native outputs have seven pages. Pages1–5 have identical full glyph records between W and L. The non-target extracted text sequence matches after excluding exactly the target paragraph and terminal page footers.

On page6:

- W is one line; both equals signs are at top281.94689pt. The next paragraph starts at295.60596pt.
- L is two lines; equals tops are280.53076pt and297.48076pt. The next paragraph starts at311.16004pt, approximately15.55pt lower than W.
- W page7 starts with “Câu6: Đáp án23.”; L page7 starts with “Giá thuê tối ưu là…” from the end of Câu5, followed by Câu6.

The earlier observation that “Tính…” moves from page6 to page7 applies to the **default-headless font path**. It is not the page-break behavior of the native path matching GUI. This review supersedes any cross-backend inference from that earlier measurement; the historical artifacts remain intact.

L therefore still changes page flow under the corrected comparison environment. Its prose prefix is vertically centered between the math rows and its shorter first math row is centered. W already fits the real page. There remains no basis to introduce automatic splitting for this case.

The complete exam is an existing Nov6 native-OMML snapshot with known issues, including six pre-existing `¿` glyphs in the earlier GUI reference. A matched renderer does not remove those issues or establish full-exam fidelity.

## Review disposition

1. **Clarified within this case:** GUI/default-headless font and layout discrepancy. Same-file controlled export plus native repeat isolates backend selection as a sufficient operational cause/remedy.
2. **Comparison prerequisite:** pin executable/version, input, VCL selection, fresh profile, font evidence and GUI reference. Same version alone did not make the earlier default-headless outputs comparable to GUI.
3. **Still open:** L layout policy, existing formula errors, full-exam source fidelity and INT semantic handling. The stale-preview packaging issue from the earlier report is independent; backend selection is not a substitute for invalidating an obsolete preview.

Recommended scratch invocation pattern on this tested Mac/build is a per-process `SAL_USE_VCLPLUGIN=osx` environment override alongside `--headless` and a new `-env:UserInstallation=file:///...` profile. Exact successful commands are in `runs.json` and `native-runs.json`; there is no permanent environment or application preference change. Scripts reject existing output directories: reproduce by copying them into a new scratch sibling, keeping their relative project depth.

## Evidence and verification

- `run_controls.py`, `runs.json`: primary same-file/default-vs-osx pair, command lines, input/output pins and logs.
- `inspect_controls.py`, `controls.json`, `*-fonts.txt`: font inventories, normalized text, page starts/ends.
- `compare.py`, `comparison.json`: full7-page glyph and pixel comparison.
- `comparison-contact.png`: GUI / default headless / native headless, pages1 and6; visually inspected.
- `run_native_review.py`, `native-runs.json`: native W/L pair and minimal native repeat.
- `review_native.py`, `native-review.json`, `native-W-L-contact.png`: native W/L page6/7 comparison, visually inspected.
- `verify.py`: fresh read-only verification of source and acceptance pins, same-input design, fresh-profile separation, glyph equality, all7 raster comparisons, native repeat and W/L control.

Verification completed successfully. Input PDFs/ODTs, executable, `docs/dsmt4_migration_acceptance.md` and `docs/dsmt4_real_corpus_2026-11-03.md` match their starting pins. HEAD remains `467370fec8e1ad82abe284f091fdd9ca3862a349`. No accepted increment, commit or push.
