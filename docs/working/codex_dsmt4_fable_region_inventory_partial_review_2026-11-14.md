# DSMT4 — partial Fable region inventory and independent Codex review (2026-11-14)

**Status: partial, not completion of the five-step handoff.** Same Claude session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, requested/observed assistant model `claude-fable-5-2`. Scratch only; no production change, commit/push or accepted promotion.

Dispatch root: `work/dsmt4-claude-region-overflow-20261113T201043/`.

## Worker progress and quota

Attempts01/02 were rate-limited before producing implementation artifacts. Attempt03 resumed after the reported reset using the installed CLI's `--autocompact 100k`. Its compact-boundary event records564,148 pre-compaction tokens and13,960 afterward, preserving the session. Fable then created and ran:

- `execution/inventory.py`
- `execution/region-inventory.json`
- `execution/inventory-pins.json`

It stopped at the next quota before writing the report, candidate proof or a W/L pair. The final quota event reports reset at `2026-11-14T06:00:00Z`, or13:00 Asia/Saigon. A CLI result subtype of `success` is not task success here: its text is the quota rejection and process exit is1.

Attempt04 is prepared with a short continuation prompt referencing the new evidence. It keeps the same session/model and100k compaction window, writes only a new `execution/continuation-04/` directory, and asks for a checkpoint first. No external scheduler or model fallback was created. At this checkpoint it has not started.

## Independent inventory check

Codex reran the worker's pure analysis functions in memory, compared the full result to its JSON, and independently counted actual embedded frames/MathML roots from each ODT ZIP:

| Exam | MathML | Retained OLE | Total |
|---|---:|---:|---:|
| Tuyên Quang | 355 | 0 | 355 |
| Tạ Quang Bửu | 115 | 0 | 115 |
| Hóa Bắc Ninh | 92 | 13 | 105 |
| Hóa Hà Nội | 100 | 0 | 100 |
| Lý Bắc Ninh | 42 | 52 | 94 |
| Total | 704 | 65 | 769 |

Retained OLE objects are counted separately; these numbers are not conversions or accepted formulas. The existing source snapshots and safety policy remain unchanged.

The worker finds148 objects in51 tabbed paragraphs. Its `unresolved_container=0` means structural block widths were obtained; it does not certify occupied tab regions, glyph containment or intended answer columns. Six tabbed objects have no explicitly declared stops; another uses mixed center/left stops. The current stop-index heuristic explicitly assumes the kth tab lands at the kth declared stop, which is not a general layout proof.

## Three width flags do not justify L

The only `WIDER_THAN_CONTAINER_LINE` flags are TQB Object47/48/49, intervals `[3,0;3,3)`, `[3,3;3,6)`, `[3,6;3,9)` in Table2, row0, columns2/3/4 (zero-based).

Codex independently measured the PDF's actual table lines and each interval's glyph ink. The intervals intrude approximately1.02–1.12pt into the right padding, but none crosses the physical cell border or collides with its neighbor. The enlarged `review/TQB-cells-1.png` was inspected.

The source DOCX's second table/first row/corresponding cells contain OLE47/48/49 with rId100/102/104 and preview image47/48/49 with rId99/101/103. Existing manifest entries map to genuine interval sidecars. `candidate-provenance.json` records exact locators and hashes. No preview reconstruction or BIN decode was used.

These are bounded intervals without a continuation relation suitable for L. No arbitrary cut or W/L pair was made. A frame-width flag alone would have selected a misleading candidate.

## Native layout evidence added by Codex

For independent review, Codex investigated the documented [Writer Layout XML export filter](https://help.libreoffice.org/latest/en-US/text/shared/guide/convertfilters.html?DbPAR=SHARED&System=UNIX). Direct CLI layout export produced only3 pages and85 object frames for the4-page/115-object TQB document. That incomplete dump is retained as a failed control and is not used as full-document proof.

A Java UNO client then opened each input Hidden/ReadOnly in its own fresh headless system-LibreOffice process, with `SAL_USE_VCLPLUGIN=osx`. It exported PDF first, followed by layout XML in the same process, using [XStorable.storeToURL](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1frame_1_1XStorable.html), without storing the source. The app's bundled Python launchers exited137; no installation/security change was attempted. Existing Java/UNO libraries supplied the successful bridge.

All five resulting pairs have the expected31 pages in total. Their PDF glyph text/font/size/boxes match the prior native controls to5 decimal places. All769 source frame names map uniquely to the full dumps. Page origins are subtracted and the20-layout-units-per-PDF-point scale is calibrated against page dimensions and the known table positions. Dynamic native IDs/pointers are not compared across processes.

`layout-index-v2.json` records actual frame/cell/paragraph print boxes. No MathML frame extends horizontally more than2pt beyond its actual paragraph print box in these dumps. This remains frame geometry, not glyph-ink or intended-tab-column acceptance.

`tab-placement-review-v2.json` compares the actual tabbed frame positions with reconstructed line portions. It matches123/148 frames;25 remain unresolved because the reconstruction does not cover all cached/missing portions or text-advance behavior. All148 frame positions themselves map; the unresolved count is specifically frame-to-line-portion reconstruction. No same-paragraph frame-rectangle intersections were found among the148. These checks do not establish all glyph/label boundaries or the intended column contract.

## Review disposition and remaining handoff

- Structural inventory is reproducible for these inputs, with704 MathML and65 retained OLE separated.
- The3 interval flags are not eligible W/L cases.
- Native layout can provide actual positions, but only after full formatting and PDF calibration; direct dump alone was insufficient.
- The25 unresolved line-portion cases and intended tab boundaries must stay explicit. Neither zero structural flags nor nonintersecting frame boxes constitutes full visual/source acceptance.
- Fable still owes the remaining five-step deliverables, including typed coverage/unknowns, candidate disposition and report/result/handoff files. If no eligible case is proven, W/L must remain `not_run_conditional`; no narrowed-column/spacer case should be manufactured.

Evidence is under `attempt-03/review/`: `check.py`, `review.json`, `candidate-provenance.json`, `uno-layout/`, `layout-batch/`, `layout-summary-v2.json`, `layout-index-v2.json`, `check_tab_placement_v2.py`, `tab-placement-review-v2.json`, `review-handoff.json` and `verify_all.py`.

Fresh `verify_all.py` passed: worker source/input pins,221 tracked files, HEAD, executable pin and prior source/acceptance pins remain unchanged;31-page native calibration,769 frame maps and the partial tab checks were reverified. No W/L case or accepted increment was created in this continuation.
