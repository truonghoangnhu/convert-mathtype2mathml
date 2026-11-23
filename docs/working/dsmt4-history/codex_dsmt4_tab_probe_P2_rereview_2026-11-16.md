# DSMT4 — tab/probe P2 rereview, 2026-11-16

Disposition: **both requested P2 findings closed for the scratch diagnostic scripts**. This does not close the25 native line-portion cases or certify intended column edges. No production integration, commit/push, W/L pair or accepted promotion. Corpus remains needs_review.

## Same-session execution

Fable5.2 resumed Claude session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`. Attempt08 completed with process0, is_error=false,30 turns and28 tool calls. All observed assistant model records are `claude-fable-5-2`. Normal CLI compaction200k was used; one compaction reduced334756 tokens to6342. Subsequent recorded input/cache totals ranged roughly33k–153k. No clear, model/session fallback, hook bypass or global-setting change was used. The run finished without quota rejection; this is evidence for this run, not a general quota guarantee.

Worker code, controls and handoff are new files under `work/dsmt4-claude-region-overflow-20261113T201043/execution/continuation-08/`. Earlier evidence remains unchanged.

## P2: skipped tab stops — closed

`build.py::classify_closure` now checks configured stops after the occupied segment start rather than after the tab start. The misleading proven-boundary label is replaced with `measured_structural_tab_closure`, explicitly excluding an author-intent claim.

Codex independently compared all148 old/new frame records. Exactly the8 previously identified Hóa Bắc Ninh frames changed class: Object6/8/18/20/49/51/61/63. Their measured occupied segments did not change. All94 remaining structural closures agree with the next configured left stop under the stated rule; the8 crossings are recorded as configured_stop_skipped. Valid neighbouring cases remain closures.

Counts reconcile as94 structural closures +8 skipped stops +45 last-on-line segments +1 center-stop unresolved case =148 frames in51 paragraphs. Among the25 open portion cases the overlap is9/4/11/1. The24-check regression and the rebuilt JSON passed. No crossing of an unused stop was promoted to a physical column overflow or a W/L case.

## P2: failure exit status — closed

`probe-v3/TabProbe.java` preserves measurement status outside cleanup:0 for completed measurement,2 for connect/load failure,3 for a failure after load. It writes/flushed-checks DONE before reporting BODY_OK. Cleanup is bounded and logged separately; it no longer overrides a measurement exception with exit0.

`probe-v3/run_probe.py` requires client0, BODY_OK, complete DONE, expected frame coverage, readable required settings, valid PDF/page count, and unchanged source. Failed cases return runner1 and retain logs. Saved evidence validates for5/5 measurements,148 frames;11 malformed-output mutants are rejected. Informational unsupported settings are reported separately from required settings.

Codex ran both fresh native controls using the final scripts, system LibreOffice with SAL_USE_VCLPLUGIN=osx, separate new profiles and ReadOnly/Hidden loading:

- **Positive:** Lý Bắc Ninh normal destination; client0 / runner0, BODY_OK,4 expected tabbed frames in2 paragraphs. The4-page PDF's glyph text/font/size/boxes match the prior native control to five decimal places.
- **Negative:** a regular file blocks the export destination's parent path, causing export failure after document load; client3 / runner1, BODY_FAILED, no BODY_OK, and no PDF/TSV output. Source hash/mtime remain unchanged.

The positive and negative application shutdowns still require bounded termination of their own private server (server255). This is recorded as non-clean cleanup. It does not become measurement failure or get described as a clean application exit. General shutdown repair is outside this two-P2 task.

## Verification and limits

Codex freshly ran the delivered verifier into a new directory: **40/40 checks pass**. It rebuilt the analysis, ran boundary regressions, checked pins/current source hashes, validated saved measurements, rejected output mutants and checked the negative-control records. Codex additionally performed the two live controls above and an independent exact-eight-classification comparison.

Fresh native-evidence verification also passed. The221 tracked files, HEAD, pinned inputs and source documents remain unchanged. A read-only secondary review confirmed the boundary correction; Codex directly reviewed the final Java/runner and independently executed the controls.

The broader handoff remains deliberately bounded:

- All25 native line-portion statuses remain unresolved_native_dump. Their alternate horizontal cursor positions are measured; their line assignment is x-reset derived, while123 other cases agree with old native line controls.
- Object22's4.649pt extra blank advance versus4.750pt dump displacement leaves0.101pt residual: justification is supported, not exactly reconstructed.
- The24 missing-portion filter explanation remains supported but not intervention-tested. The earlier claim that recovery with the filter is impossible was withdrawn.
- The94 structural tab closures do not prove intended column edges. The54 per-frame operational unknown records and the global intent/geometry/source limits remain explicit.
- These measurements concern the existing Nov6 Writer snapshots, not full semantic acceptance of the current converter or corpus.

## Evidence

Worker handoff: `execution/continuation-08/{report.md,result.json,review-handoff.json,verify.py,test_boundary.py,build.py,tab-boundary.json,line-portion-cases.json,unknowns.json,pins.json}`.

Codex evidence under `attempt-08/codex-review/`:

- `verification-01/verification.json`: fresh40-check run.
- `positive-control/runs.json`, `positive-pdf-verification.json`: normal native control and glyph comparison.
- `negative-control/runs.json`, `negative-control-exit.json`, stdout/stderr: independent export-failure control.
- `final-review.json`: independent exact-eight change check, unchanged148 segments, source/tracked pins and final disposition.
- `session-verification.json`: observed model, compaction and worker outcome.

The two scratch P2 fixes are review-complete. The remaining native-portion/intent questions require a separately scoped continuation; accepted stays unchanged.
