# Final follow-up: line-metrics resolutions and the UNO helper (2026-11-11, read-only)

**Verdict:** I found no P1 or P2. The three P3 fixes and the helper correction are reported narrowly and accurately. Two small P3 provenance items remain, plus one stale sentence. Status stays scratch, needs_review, accepted 0, with no UI round-trip claim.

## Earlier P3 items: resolved
1. **Source ink on the unshaded control.**
   - `verify_source_ink_control.py:4-5` requires the 600 dpi crops from the control PDF and the border probe to be pixel-identical (empty difference bounding box). Both must give 50.52pt.
   - `source-ink-control-check.json` records `raw_600dpi_crop_pixels_identical: true`.
2. **Source column now comes from a script.** `compare_height_trials.py:12-13` computes the source stem sum, p11 band, allocation, and the before/after gaps from `word-border-envelopes.json`. It asserts the bands sit on the same page, and the source PDF is labelled.
3. **Instrument note.** Report line 37 now says the border and shading rows are different instruments, and that only the allocation and ink rows are comparable.

Also fixed: answer markers now bind as an exact multiset (`anchor_geometry.py:15`, `sorted(found)==sorted(expected)`), so a duplicate plus a missing marker can no longer pass.

## UNO helper: correct as reported
- **Macro mode.** `LayoutDump.java:25` uses the named constant `MacroExecMode.NEVER_EXECUTE`, which is 0. The old numeric 4 is `ALWAYS_EXECUTE_NO_WARN`, so the correction (report line 60) is accurate. Files also load with `ReadOnly=true`, `UpdateDocMode=0` and `Hidden`.
- **Profile isolation.** `LayoutDump.java:17-19` resolves the remote `$(user)` path and compares it to the expected profile path before creating the Desktop. A mismatch prints the error and calls `System.exit(2)`.
  - The comparison works on whole path components, so a prefix collision such as `…-v2-evil` cannot match.
  - This also covers the race in `run_complete_layout.py:11`, where the reserved port is released before `soffice` binds it. If another listener grabbed the port, its profile would not match.
- **Guard tests.** `run_complete_layout.py:23-26` checks that the wrong-profile run fails, with the expected message on stderr, before the positive run. The isolation JSON (lines 2-9) shows return code 0, stdout "Verified isolated profile", and a negative exit code of 2.
- **Run hygiene.** The runner refuses to reuse a profile or overwrite outputs (`:8,12`), and always terminates the listener (`:29-31`).
- **Re-export check.** `verify_writer_reexport.py:9-15` confirms there are no `vba` parts and no `macroEnabled` content type. It then requires identical PDF word geometry and identical `extract()` output (every line, frame, fly and flag) between `writer-complete/` and `writer-verified/` for all 6 documents.
- **Current inputs.** `extract_writer_metrics.py:35` and `render_math_crops.py:12` now read `writer-verified/`, so "current metrics read verified outputs" is true.

## P3 items still open
1. **The positive-profile geometry match has no generator script.**
   - `complete-layout-run-isolation-check-v2.json:12` contains `geometry_matches_verified_baseline: true`.
   - `run_complete_layout.py:28` does not write that key, and no `.py` file in the folder computes it. The only other reference is a pointer in `targeted-checks-final.json:71`.
   - Report line 66 rests on this boolean. Add the comparison of `writer-isolated/Toan-native` against `writer-verified/Toan-native` (PDF words plus `extract()`) to a saved script, as `verify_writer_reexport.py` already does.
   - As it stands, rerunning the runner would also drop the key.
2. **Unauthenticated loopback listener.** While running, `soffice --accept` listens on loopback without authentication. The ephemeral port and the profile guard limit the risk, and this is scratch only. Worth one line in the limits section.
3. **Stale sentence.** Report line 64 says "Claude chưa kiểm các sửa P3 cuối hoặc helper UNO" (Claude has not yet checked the final P3 fixes or the UNO helper). After this review it is out of date; mark it superseded rather than editing history.

## Claims checked as scoped
- The text says "PDF text geometry" and layout metrics, not raster equivalence. The only raster equivalence claimed is the source ink crop, which is checked separately.
- No global macro setting is changed. Every setting is a load-time property on a read-only load inside a dedicated profile.
- There is no UI or acceptance claim. The UI checks in `work/dsmt4-height-ui-2026-11-11` are not evidence here, and I did not open them.

## What I inspected
- **Report:** lines 26–67, covering the table note, limits, "Helper correction" and "Review resolution", including the backend isolation paragraph.
- **Read in full:** `LayoutDump.java`, `run_complete_layout.py`, `verify_writer_reexport.py`, `verify_source_ink_control.py`, `source-ink-control-check.json`, `complete-layout-run-isolation-check-v2.json`.
- **Searched only:**
  - `compare_height_trials.py:12-13` and `anchor_geometry.py:15`;
  - the `writer-verified`/`writer-complete` paths in all `.py` files;
  - `geometry_matches_verified_baseline` across the folder;
  - `targeted-checks-final.json:71`;
  - a listing of the `writer-verified/` PDFs.
- **Not opened:** `writer-reexport-check.json`, `complete-layout-run-verified.json`, the `writer-isolated/` outputs, any listener logs, and all images.
