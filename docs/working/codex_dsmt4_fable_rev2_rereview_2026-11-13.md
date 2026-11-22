# Codex independent rereview: two P2 and one P3, revision 2

Implementer revision: `work/dsmt4-fable-five-phase-rev2-2026-11-13/`. Claude resumed the same session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80` on requested model `claude-fable-5-2` after the advertised05:10 reset. The execution completed successfully in9 turns. Scope was only the three findings from `codex_dsmt4_fable_five_phase_review_2026-11-13.md`; original candidate, measurements and evidence were retained.

## Verdict

**P2-1, P2-2 and P3-1 are closed within this scratch revision.** No new actionable finding in the reviewed delta. This closes the guard/measurement findings, not production integration, semantic fidelity, GUI acceptance, or the five-phase project objective.

## P2-1: ancestor-context bypass — resolved by narrowing

Candidate v2 requires every bar-like text occurrence to be a direct child of the math root, and a plain attribute-free `mo` bar. All bars under mrow, mstyle, mfenced, fractions, scripts and other ancestors are rejected rather than being accepted through a shallow parent check. The original reviewer nested-fence and styled-ancestor probes reject with exact input preservation.

I additionally generated depths1–10 of plain mrow, mfenced-ancestor and styled-ancestor contexts: all reject unchanged. The implementation does not claim to support those shapes. This conservative reduction is consistent with the requested correction.

## P2-2: nested-interior grammar bypass — resolved by narrowing

The pair interior is exactly one item from the documented finite list: plain mi/mn leaf or the specific accent-vector mover shape. No mrow, nested fraction, relation or other nested construct is accepted merely because its forbidden operator is hidden below a direct child. The original nested-relation and nested-fraction probes reject exactly. I also generated relations wrapped in1–10 mrows; all reject unchanged.

The24-test suite explicitly compares v1 versus v2 to demonstrate the original failures, tests exact preservation/idempotence and exercises the retained real positives. The verifier inventories all27 original bar sidecars. The three previously measured survivors have byte-identical K output and prepared application input to the prior measured files; no new render is claimed. A measured `|integral…dx|` positive is deliberately dropped and returned to the unchanged failing source candidate. Two other vector-norm sidecars fit the finite grammar but remain unrendered and are visibly marked needs_measurement. These are coverage limits, not accepted cases or a hidden expansion of empirical evidence.

## P3-1: page-end formula bounds — resolved for the generated documents

The new measurer identifies the known label, SPACER and sentinel strings and removes those body regions; it no longer assumes the first word on each page is a label. If expected marker identity/count cannot be established, it returns inconclusive without coordinates. Old measurements.json remains unchanged and its page-end formula fields are explicitly superseded.

I independently recomputed bounds from the existing PDFs using exact body WORD boxes and subtraction from the raw page glyphs, rather than the implementer's line-grouping routine. The corrected formula boxes match on all14 pages across8 long/fraction page-end documents. In particular:

- long spacer384 page1 has only label/SPACER and null formula;
- its page2 includes both `h(x)=f(x)−g(x)` and the continuation `=ax…`;
- long spacer372 page2 contains only the sentinel and null formula;
- fraction spacer372/384/396 puts the formula on page2, with page1 formula null.

I viewed the corresponding long384 two pages, long372 sentinel-only page and fraction384 continuation page individually as PNGs. These images agree with the corrected classification. Coordinates remain text-glyph bounds, not ink bounds; fraction rules, drawn fences and clipped drawing are outside this metric. It remains a generated-page diagnostic, not full-exam layout acceptance.

## Fresh verification

- `test_v2.py`:24 tests passed.
- `verify_rev2.py`: passed, including the unmodified19-test v1 suite, v1/v2 matrix, exact survivor application-input bytes, all8 corrected documents, pinned files and recorded git-state checks. This was run before adding this reviewer report to the repository; its snapshot check will naturally detect later repository changes.
- Reviewer `work/dsmt4-codex-rev2-review-2026-11-13/recheck.py`:63 pinned files checked,4 original reviewer probes rejected exactly,40 additional depth/context negatives rejected unchanged,14 page bounds independently confirmed. Results in that directory's result.json. No renderer was launched by the reviewer.
- `git diff --check`: passed.

No production source, corpus status, input fixture, old output or Git HEAD was changed by this revision. New code and corrected measurements are in a new scratch directory; this report is a new reviewer document. No commit/push/merge, accepted promotions0, corpus remains needs_review, FULL_END_ONLY and safety skips unchanged.

## Still open

K v2 remains a scratch candidate. GUI/edit/save-close-reopen, the two unrendered norm cases, ordering against existing B/G rules, full-exam layout, tall shapes, Word route, source/MTEF semantic review and occurrence-level acceptance remain incomplete. INT is not fixed by this revision. Current GUI blocker remains Math object activation through CUA; Finder access had succeeded. Closing these three findings does not authorize integrating K or increasing accepted.
