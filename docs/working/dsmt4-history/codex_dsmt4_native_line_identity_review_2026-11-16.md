# DSMT4 — native line identity review, 2026-11-16

Disposition: **native line identity measured and reviewed for25/25 previously open cases**. The geometric diagnostic no longer depends on x-reset inference for these frames. Literal SwParaPortion/FlyCnt reconstruction remains unresolved for25 cases; source semantics and intended tab-column edges are not certified. Scratch only, no commit/push, W/L pair or accepted promotion. Corpus remains needs_review.

## Focused experiment and outcome

Fable5.2 continued session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, attempt09, using the existing200k compaction configuration. It measured only the two Chemistry snapshots containing the open cases, not all five exams. The new Java probe queries the native view cursor's XLineCursor interface, snapshots line starts/ends with independent model cursors, and compares range starts to identify shared native lines. Locator offsets do not reconstruct formula content.

The [official XLineCursor interface](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1view_1_1XLineCursor.html) provides start/end navigation within laid-out text. The installed interface signature is also retained under the worker's refs directory. The document is opened Hidden/ReadOnly with macros disabled in fresh private system-LibreOffice profiles, SAL_USE_VCLPLUGIN=osx. PDF is exported before probing. No document text or source save is performed.

Two measurement bodies succeeded, with bounded forced cleanup of their private servers recorded separately. Evidence covers28 tabbed paragraphs,69 frame anchors,2595 membership records and52 distinct native line snapshots.

## Independent Codex review

Codex read the Java measurement and analysis code and independently parsed the raw LS/LN/PORT records. Checks establish:

- All25 target frame anchors have a native line identity, matching the previous x-reset result. This is now native API evidence, not merely confirmation by another coordinate heuristic.
-44/44 control frames with existing native dump portions have matching line indices. These include Object6/7 on the same line and Object22/23 on separate lines.
-52 native line snapshots have valid monotonic starts, nonnegative locator offsets, ordered endpoints and successful native start/end flags. Frame names and coordinates in membership records match the corresponding measured portion records.
-Object23 is at the shared model boundary offset103; native API assigns it to line1, agreeing with the old native dump. Object22 is on line0. Object67's centered paragraph is single-line. Boundary affinity is recorded rather than guessed from glyph height.
-All16 newly exported PDF pages match prior native controls in glyph text/font/size/boxes to five decimal places. Source pins and the221 tracked files/HEAD remain unchanged. Fresh older native-evidence verification also passed.

No new visual layout was introduced, and existing representative visual checks remain applicable to these matching native PDFs. The two prior P2 corrections and tab classifications94/8/45/1 remain unchanged.

## Verifier correction and completion evidence

The worker reached the five-hour quota after saving scripts, measurements, case dispositions, report/result and handoff (18 tool calls,20 turns, process1). This was not a successful worker process exit and is not represented as one.

Its verifier returned43/44 because a phrase filter rejected the report's statement that24 ambiguous boundary positions were “all resolved to the later line.” That statement concerns line affinity, not closure of all portion cases. Codex retained the original failed verification and made a separate verifier copy under attempt09/codex-review. The copy narrows the prohibited claims to actual blanket case-resolution statements; all native/data/pin/status checks are preserved, including the explicit25 unresolved literal portions. Worker files were not overwritten.

**The reviewed verifier passed44/44 checks** in a new output directory. Independent raw-record and PDF checks are saved separately. This review closes the operational native-line-identity question without waiting for another quota window. It does not claim recovery of missing dump XML.

## Remaining limits and next decision

The24 missing native dump portions remain a typed tool limitation; Object22 retains its0.101pt spacing-reconstruction residual. Dump-filter causality is supported but not intervention-tested. Only one dump-matched control is on a line above index0; higher-line targets additionally rely on direct native range evidence and the recorded consistency checks. Trailing-blank semantics of gotoEndOfLine were not investigated.

Intended tab-column edges, vector-only paths/clipping, retained OLE geometry and mathematical source equivalence remain outside this result. These are separate acceptance questions. Repeating dump reconstruction is unnecessary merely to establish which native line contains the25 target anchors.

Evidence root: `work/dsmt4-claude-region-overflow-20261113T201043/`.

- `execution/continuation-09/`: raw run-01, probe Java/runner, case-disposition.json, native-lines.json, controls.json, pins.json, unknowns.json, report/result/review-handoff and original verifier.
- `attempt-09/codex-review/independent-review.json`: independent69-frame/25-target/44-control/52-line/16-page checks.
- `attempt-09/codex-review/verification-01/`: original phrase-filter failure, preserved.
- `attempt-09/codex-review/verify_reviewed.py` and `verification-02/verification.json`: corrected verifier copy and44-check pass.

Accepted stays unchanged; no production edits or integration were performed.
