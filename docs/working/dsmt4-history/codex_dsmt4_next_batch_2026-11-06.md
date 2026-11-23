# DSMT4 next compatibility batch — 2026-11-06

Status: **needs_review**. This batch adds verification evidence and rejects an unsafe representation change; it does not add a production converter rule or promote any occurrence to accepted. The last production output remains `out/dsmt4-writer-comparison-2026-11-06/` (116 Java tests and gate4/4 recorded in its report).

## 1. Labeled-arrow investigation

Nine probes cover the three actual equations containing labeled group characters in the five-exam subset (hoa037, hoa042 and hoa086, the last with two arrows). Each compares existing `groupChr` with `limUpp` using the arrow as base, then the same limit with explicit argument size zero. Original equation tokens, labels and arrow characters are used; no source, fixture or production XML is edited.

Installed Writer importer `handleGroupChr()` emits the label as the base and arrow as `csub`/`csup`; its `vertJc` is not used to restore the intended arrow role. Initial and reopened Writer renders confirm tiny arrows beneath normal-size labels. `limUpp` improves this role assignment, but the arrows are fixed width.

Word was opened on the nine-probe document and all variants viewed together. In the ZnS → ZnO → Zn example, existing group characters stretch across their labels, whereas both `limUpp` variants have visibly shorter arrows and different spacing. **The replacement is rejected for the shared Word converter.** Explicit argument size zero does not restore stretching. The Word screenshot is `work/dsmt4-next-batch-2026-11-06/arrow-probes-v2/word-ui-comparison.png`; Writer renders and saved DOCX are beside it. A Word PDF export was requested but no resulting file was located, so it is not credited as evidence. This phase does not claim Word edit/save/reopen for the alternate representation.

The existing separate Math route remains the route to investigate for Writer editing. General Writer DOCX labeled-arrow fidelity stays open; preserving text or arrow counts is insufficient.

## 2. Nested Math system toan016

A scratch annotation preserves a one-cell outer matrix around the already bounded three-row assignment command. The prepared presentation subtree is retained. Initial and saved/reopened renders retain complete rows `x=2+5t`, `y=2+2t`, `z=1+3t`. Measured row-start spread is **0.45 pt** for the unchanged current input and **0 pt** for the prototype, in both renders.

The unchanged input is already within the earlier 0.5-pt measurement tolerance, and was visually inspected. No larger content failure was reproduced. Adding another authoritative annotation rule for this small difference is not justified in this batch: **production remains unchanged**, the nested-shape diagnostic remains, and the prototype is available for Claude review. Evidence: `work/dsmt4-next-batch-2026-11-06/nested-math-probe/` including complete-row measurements and reopened image. No UI edit or full-document placement pass is claimed.

## 3. Recheck of 36 historical Math import failures

All 36 current prepared candidates that failed Math import in the historical ledger were newly embedded in an isolated ODT, rendered, saved as ODT and rendered after reopening. The entire reopened page was viewed and compared with the corresponding prepared formula structures. The previously recorded stray fences, interval parse errors, lost charge suffixes, bare-bar failures and Celsius parse error were not observed; toan015 rows are left aligned. The initial and reopened page PNGs are pixel-identical. Text/annotations have no `¿`, `<?>` or replacement-character markers; these scans support the visual check rather than substituting for it.

This is an **isolated Math import/render/save/reopen check**, not 36 UI edits, DOCX compatibility, full-exam layout acceptance or a new audit of all 265 source formulas. Full source-to-render semantic acceptance remains open. No historical verdict is deleted or blindly transferred.

Evidence: `work/dsmt4-next-batch-2026-11-06/math-historical-failures-current/visual-review.json`, 36 object annotations, isolated ODT and PDFs/PNGs. The derived `current-ledger.json` in the batch folder attaches exactly these 36 scoped observations to the preceding current artifact mapping. All 265 identities and prior evidence are retained; **accepted promotions remain 0** and the full current failed total is not established.

## 4. Review handoff and remaining limits

A one-time app schedule was created for **07 Nov 2026, 01:35 Asia/Ho_Chi_Minh**, to resume the same Claude Code session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80` for read-only independent review. Its handoff is `work/dsmt4-next-batch-2026-11-06/review-handoff.md`. The scheduled review has not happened yet; credit availability is not assumed.

Review priorities: the previously implemented leading-temperature `>` grouping and boundary tests; whether any scope claim exceeds application evidence; the rejected arrow variants; the nested-table prototype and current 36-case Math evidence. No new production tests were needed for these scratch-only probes. Production sources have not changed in this batch; no full-test repetition is credited.

Outstanding: Writer DOCX labeled-arrow layout, full pagination/font/spacing, broader interactive editing coverage and independent final review. FULL_END_ONLY remains unsupported; old safety skips and the two OLE in Lý paragraph 91 remain retained. Nothing is committed, pushed, merged or published, and Draft/auto-merge settings are unchanged.
