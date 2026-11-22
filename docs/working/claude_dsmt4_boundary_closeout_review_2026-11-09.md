# Final review: Word comparison, box inventory and UI-saved renders (2026-11-09, read-only)

**Verdict:** I found no P1 or P2 problems. The new claims are factually correct and correctly scoped. Two small provenance gaps (P3, below) are worth closing. The basic gap in P2-3 (no Word rendering at all) is now closed. The wider cross-app round-trip question and P2-1 (common spacing) remain open. Status stays needs_review, accepted 0, and there is no production change.

## Claims checked against the evidence

| Claim | Evidence | Result |
|---|---|---|
| In Word, the boxed nine-term formula is clipped | `word-overflow-opened.png`: the line is cut at the right edge after `+19012345…` and the closing fence is missing | Correct |
| In Word, the unboxed version breaks at operators and stays complete | `word-overflow-no-box-opened.png`: two lines ending `…+2123456778)` | Correct |
| Writer clips the unboxed version too | Earlier A/B result (pixel-identical) | Correct; "no global box removal" follows |
| The Writer UI-saved six-term file breaks inside the formula in Word | `word-writer-ui-wrap-opened.png`: break after `1679012334 +`, then `1790123445)` on the next line | Correct |
| Word keeps the edge-tall question and answers together on page 1, unlike Writer | `word-edge-tall-target-opened.png`: Câu 1 and A–D above "Trang 1", Câu 2 on page 2 | Correct; the discarded non-target screenshot is properly excluded (`word-open-observations.json:23`) |
| Writer strips every outer box, not just the edited one | `all-math-box-inventory.json`: baseline 110/115 (maths 46–50 have no outer box); all 3 UI saves and all 4 headless saves go to 0 | Correct. `resolution.md:28` limits the claim to these samples, which is right |
| UI-saved files render to 4 pages and the text positions match the probes | `ui-saved-render/summary.json`: tall 169.058/199.008, wrap 160.608/175.308/211.708, edge 729.058 (page 1)/26.858 (page 2) | Correct. The earlier "Page 1 of 2" status bar was misleading and is rightly no longer cited (`:29`) |

The inventory also shows a side fact worth noting. The headless "tall" input already had the box on math 1, so the oMath that Word saved kept its outer box. Word preserves the box; Writer drops it.

## P2-3: what is now closed and what stays open
**Closed:** the basic omission of never having rendered these probes in Word. Word has now opened all four deterministic probes and all three Writer UI-saved files, as a visual check.

**Still open:**
- **Edit/save/reopen in Word.** These were open-only views, with no PDF measurements (`word-open-observations.json:24-30`).
- **The box trade-off in Word.**
  - With the box, an overwide formula is clipped.
  - Without it, the formula wraps.
  - Writer clips either way.
  - Any Writer save removes the box, which changes how Word breaks the formula afterwards.
  - Do not change policy until real source equations are shown to come near the page width.
- **Pagination differs between apps.** On the same edge probe, Word fits the question and answers on page 1 and Writer splits them. This is further evidence that one spacing value is unlikely to match both apps, so P2-1 stays open.

## P3 gaps
1. **Show that Word didn't rewrite the input files.** The Word title bars read "— Saved to my Mac". That is Word's location label, not proof a save happened, but the JSON states "no Word edit or save" without hash evidence. A sha256 of the `pre-ui-diagnostics/*.docx` files and the UI-saved files, taken after the Word viewing and compared with earlier hashes, would close this. Earlier hashes exist for the UI-saved files in `ui-roundtrip-verification.json`.
2. **Record the Word build in `word-open-observations.json`.** Zoom was 125% throughout, so this is only about reproducibility.
3. **Fix a garbled heading.** `resolution.md:9` reads "P2-3 open-only comparison completed". Suggested wording: "P2-3: basic Word open-only comparison completed; round-trip/measurement limits remain open".

**Status:** needs_review, accepted 0, FULL_END_ONLY unsupported, original safety skips and Lý ¶91 unchanged. Not production-ready.
