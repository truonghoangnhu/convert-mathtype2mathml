# Codex independent review of Fable five-phase execution

Reviewed root: `work/dsmt4-fable-five-phase-2026-11-13/`. Execution resumed the requested session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80` with requested model `claude-fable-5-2` after the advertised reset, at 00:11 Vietnam time. The runner ended with an API usage-limit error after38 turns (next advertised reset05:10). It produced an inspectable partial handoff, not a completed five-stage acceptance run. Original retry/error artifacts are retained separately.

## Verdict

Useful bounded diagnostic evidence; **do not integrate candidate K or promote corpus**. Two P2 guard gaps in the scratch candidate and one P3 measurement issue remain. Phase2 UI acceptance, phase3 tall/full-exam/Word route and per-occurrence acceptance are incomplete. No P1 found within the reviewed scope; this is not an exhaustive full-branch review.

## Findings

### P2-1 — Existing-fence/style context guards check too few ancestors

`phase4/bar_pair_candidate.py:76–79` checks only the immediate bar container and its immediate parent. The design says existing fence arguments and styled/unsupported container contexts are rejected. However, an extra mrow bypasses that boundary:

```xml
<mfenced open="(" close=")"><mrow><mrow><mo>|</mo><mi>x</mi><mo>|</mo></mrow></mrow></mfenced>
```

This returns `changed`. A pair inside `mstyle mathvariant="bold"` → `mrow` also returns `changed`. These ancestor contexts were not part of the four measured application cases. Traverse/validate all relevant ancestors with a precisely documented grammar, or conservatively reject them; add near-miss regressions. Do not widen measured support from a shallow check.

### P2-2 — Nested interior syntax bypasses the supposed bounded grammar

`phase4/bar_pair_candidate.py:87–98` checks start/end/forbidden operators only for direct children. `<mo>|</mo><mrow><mi>x</mi><mo>=</mo><mi>y</mi></mrow><mo>|</mo>` is accepted although the equivalent flat relation is rejected by the candidate's own tests. An unmeasured mfrac interior is also accepted without a supported-subtree grammar. A harmless grouping wrapper therefore changes rejection into transformation. This does not establish a particular mathematical misinterpretation, but it violates the promised fail-closed measured scope and can introduce grouping/fence behavior in untested shapes. Define the recursively allowed subtree grammar and context rules, or reject nested interiors until independently measured. Preserve unsupported input byte-identically.

Both findings were reproduced against the pinned candidate, not inferred from its description. Inputs, reports and output XML are retained in `work/dsmt4-codex-five-phase-review-2026-11-13/adversarial-K.json`. All four probes returned `changed`; the existing19 tests still pass, showing the coverage gap. K remains scratch-only and is not approved.

### P3-1 — Page-end “formula” coordinates contain spacer text and omit first formula lines

`phase3/run_long_tall.py:38–46` assumes the first word on every PDF page is a label and counts every later character before the sentinel as formula. On page1 of a page-end probe it includes the SPACER text; on page2 the first word is actual formula content and is removed from the measurement. Concrete record: `C-pageend-long-L-split-spacer384` page1 has only label/SPACER but non-null formula bounds; page2 labels `h(x)=f(x)−g(x)` as the page label and excludes that first line from its formula bounds. These coordinates must not be used as formula-height/placement acceptance. Separate label/spacer/formula/sentinel identities, and set formula bounds null when no formula is present. Existing image-based whole-object relocation observations can remain explicitly separate.

## Independent checks performed

- Re-ran the19 candidate unit tests: passed. This confirms their current assertions, not safety of untested shapes.
- Recomputed phase1 and phase4 verifier assertions from existing saved ODT/PDF artifacts, redirecting output into reviewer scratch without overwriting implementer results. Exact generated JSON matches the recorded results.
- Rechecked all18 pinned inputs/helpers/candidate hashes, HEAD and repository status against the implementer snapshot: unchanged. No production integration or commit occurred.
- Ran `git diff --check`: passed.
- Viewed individually: INT single original and both-bars-mtext; all3 wide table controls; long-formula wide baseline; nested-fraction baseline; all3 narrow long-formula comparison pages. These views support their respective narrow visible outcomes. I did not visually review every page in the handoff or claim full-exam fidelity.

Reproducible reviewer checks: `work/dsmt4-codex-five-phase-review-2026-11-13/recheck.py`; result in `recheck-result.json`. Reviewer outputs and observations do not assert a fresh renderer rerun or GUI roundtrip.

## Measured progress and remaining work

1. **INT:** The diagnostic in-place mo→mtext controls support a causal role of bare-bar import in the measured parse/render failures, including table collapse. Both-bars control keeps bars/equals/integrals and removes markers; the two single-bar controls distinguish contributions. This is not a semantic/source repair: token role changes, integral binding remains unproven. INT remains unresolved.
2. **GUI:** Fable could only prepare inputs/handoff. Codex then successfully accessed Finder and opened the scalar scratch in system Writer. Object activation via CUA failed: coordinate actions at the visible object returned AXError.notImplemented, while AX double-click selected inline object text. A Return experiment replaced that selection with a paragraph, was undone, and the scratch document was closed via Don't Save. Input SHA matches the handoff after closing. No constant edit, Math Commands capture or UI save-close-reopen succeeded. `GUI-attempt.json` records this new blocker; Finder denial is no longer the current blocker. No other user's Word/Writer document was closed or edited.
3. **Long/layout:** A genuine longer formula has a clean wide baseline and overflows the180pt synthetic column while remaining on the400pt page. Manual L split fits that synthetic column; raw split loses the leading relation. Tall nested candidate is inconclusive, full-exam copy/render was not run, and Word roundtrip/minus-delta work remains. Synthetic page-end evidence does not replace real occurrence layout.
4. **Rule design:** K is a scratch prototype with useful fail-before/pass-after evidence on four real sidecars, but ancestor/interior guards are not closed and B/G ordering/all relevant corpus cases/GUI remain untested. Saved presentation reimport regroups Commands; no correspondence or semantic acceptance follows.
5. **Acceptance:** Criteria proposal is useful. The matrix is a preliminary summary with aggregate rows, not a completed occurrence-by-occurrence corpus ledger; it must not drive promotion. All proposed changes remain needs_review/unsupported as applicable; accepted promotions0, FULL_END_ONLY and safety skips unchanged.

## Next handoff after capacity is available

Resume only the same authorized Fable session. Address P2-1/P2-2 with a narrow versioned scratch candidate and real negative tests before rerendering anything; retain existing candidate/results. Correct page-end metrics in a new result file without rewriting prior evidence. Record the updated GUI blocker and leave UI acceptance pending until Math editing can be reliably operated through permitted CUA. Finish actual full-layout coverage and occurrence-level evidence before claiming the five-stage objective complete. No automatic model/session fallback, production change, commit/push/merge or accepted promotion is authorized by this review.
