# DSMT4 — native tab probe review, 2026-11-15

Disposition: **partial handoff, two P2 findings open**. Same Claude session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, model `claude-fable-5-2`. Scratch only; no commit/push, W/L pair or accepted promotion. Corpus remains needs_review.

## Findings requiring correction

**P2 — eight skipped-stop cases are falsely classified as proven boundaries.** `execution/continuation-07/build.py:67–73,195–202` computes skipped stops after the current tab's start, but its claimed rule requires the first configured stop after the occupied segment's start. Current Hóa Bắc Ninh Object6/8/18/20/49/51/61/63 each identify the next configured stop as index1 at198.461pt, then claim a proven right boundary at index2,325.991pt. Object6's segment already ends at233.809pt. The intermediate stop has been passed; filtering only after that position hides it. Under the worker's rule these eight belong to skipped-stop cases, reducing102 to94 rule-consistent tab closures. Even those94 do not independently certify author-intended column edges.

**P2 — probe failures can be returned as success.** `v2/TabProbe.java:83–88` unconditionally calls System.exit(0) from finally, masking exceptions in PDF export or traversal after loading the document. `v2/run_probe.py:29–44` records return codes without requiring a complete DONE record, valid outputs or expected coverage before finishing successfully. Preserve measurement failure status separately from bounded cleanup; require completion/output/coverage checks and a negative failure control. This is a reproducibility defect; the independent checks below establish that the currently saved datasets are complete despite it.

**Qualification — Object22 is not exactly reconstructed.** Its measured extra blank advance is4.649pt versus the dump displacement4.750pt, a0.101pt residual. This supports justification as the explanation but does not establish exact spacing reconstruction. Also, “not recoverable with this filter” in unknowns.json is stronger than the recorded supported-but-not-intervention-tested filter hypothesis. Keep causal uncertainty explicit.

## Progress independently verified

Worker artifacts: `work/dsmt4-claude-region-overflow-20261113T201043/execution/continuation-07/`.

- A native UNO probe measured all148 named MathML frames in51 tabbed paragraphs:13/8/18/10/2 paragraphs across the five existing Nov6 ODT snapshots. Every TSV has a complete DONE record and no missing frame coordinates. No source save or GUI automation was used.
- Horizontal calibration against native frame boxes has maximum residual below0.016pt; measured frame widths agree within0.028pt. Page numbers agree. Raw cursor Y is not page-local vertical geometry; it must not be used as a native line box.
-123 previously matched frames have the same line index in the new analysis as their old native portions. There are119 native tab-width controls; maximum discrepancy0.022pt. Lines for the25 remaining cases still rely on alternate cursor/order geometry rather than recovered native FlyCnt portions.
- All25 cases now have measured alternate horizontal positions. Their native portion status remains unresolved_native_dump. Of these25, the corrected projection under the worker's own rule is9 rule-consistent tab closures,4 skipped stops,11 last-on-line segments and1 center-tab case with unresolved intended boundaries.
- Hóa Hà Nội Object67's segment aligns to the configured center stop within0.020pt. This clarifies alignment, not intended column edges. Six default-stop Hóa Bắc Ninh occurrences and their paragraph context remain separately represented in the raw probe; current DOCX definitions were not compared.
- All31 newly exported PDF pages match the prior native controls in glyph text/font/size/boxes to five decimal places. Source hashes/mtimes and221 tracked files/HEAD remain unchanged. All saved output/input pins match.
- A fresh build into a new Codex-owned directory reproduced all four worker JSON files byte for byte. Reproduction does not validate the erroneous boundary classification.

The probe implementation's coordinate origin was checked against the [official source at the installed revision](https://raw.githubusercontent.com/LibreOffice/core/bce0998afefdbc355585ca324285661a2170ba77/sw/source/uibase/uno/unotxvw.cxx): it subtracts page-master spacing and document border from the native character rectangle before unit conversion. This explains why raw cursor coordinates cannot simply be treated as PDF page coordinates. A local source download returned HTTP503; no local whole-file source hash was claimed. The viewed-source note is retained.

## Cleanup and representative visual review

The first Hóa Hà Nội trial finished writing its measurements but hung during dispose/terminate. It was preserved as a failed control with client143/server255. The worker stopped only its own private-profile processes.

The revised probe completed all five datasets with client0. Its shutdown helper still hung in all five cases; parent cleanup terminated the private server, yielding server255. Those are completed measurements with bounded forced cleanup, not five clean application exits. The unconditional-success defect above must be repaired.

Codex visually reviewed native contexts for Hóa Bắc Ninh Object6/7 and Hóa Hà Nội Object67. The first shows two separated answer groups: crossing an unused configured stop does not establish a physical column overflow. The second shows the centered equation segment and following paragraph without a visible collision. These are visual observations, not source-semantic or pixel-mask acceptance. Pins/crops are in `attempt-07/codex-review/visual-review.json` and `tab-context-contact.png`.

## Blocker and next handoff

Attempt07 stopped after7 tool calls with process1 and is_error=true due to the five-hour quota, reset epoch1794754200: **21:50 on2026-11-15 Asia/Ho_Chi_Minh**. It produced the probe, checkpoints, build.py and build-01 JSON, but no final worker report, result, verifier or review-handoff. The user's full requested handoff remains incomplete. No retry loop or automation was created.

Observed request input/cache totals grew from roughly238k to308k tokens across this short run under auto compaction. This is a concrete context-cost concern, not a proven explanation of quota accounting. The next checkpoint proposes a single-variable test of the normal CLI compaction window at200k, preserving session/model/guards;100k previously thrashed. This adjustment has not yet been run and is not claimed as a fix.

Next instructions: `attempt-07/next-resume.txt`. Fix the two P2 issues in new scratch files, qualify the Object22/filter-cause claims, regenerate into new directories, and finish the report/result/unknowns/pins/verifier/review-handoff. Keep native-portion and intended-boundary residuals separate. Do not force W/L from the eight skipped stops.

Codex verification: `attempt-07/verify_review.py` passed into `codex-review/verification-01/review.json`; `review-supplement.json` records the123 native-line controls, corrected25-case projection and identical reproduction. A separate read-only reviewer independently confirmed both P2 findings and calibration/coverage facts. No worker evidence was overwritten.
