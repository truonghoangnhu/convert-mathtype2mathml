# DSMT4 — Fable region handoff final review, 2026-11-14

Disposition: **reviewed scoped negative, with explicit unresolved coverage**. The five-step diagnostic handoff is complete at this scope; steps3–4 remain conditional and were not run. This does not complete the project or certify the full exams. Scratch only; no commit/push or accepted promotion.

## Worker and recovery

Claude Code resumed session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, using only observed assistant model `claude-fable-5-2`. Attempt04 stopped with autocompact thrashing after creating its checkpoint. Attempt05 changed only the explicit compaction window from100k to the CLI's normal `auto` mode; session, model, tools and guard were preserved. No clear, fallback or guard bypass was used.

Attempt05 finished with process exit0, `is_error=false`,10 turns and9 tool calls, without a compact event. This supports the window adjustment for this run; it does not prove the origin of all request overhead or a general Claude fix. Logs and immutable before-pins are in `work/dsmt4-claude-region-overflow-20261113T201043/attempt-05/`.

The worker created new files only under `execution/continuation-05/`: analysis and verifier scripts, occurrence/coverage/candidate/pin JSON, report/result/review-handoff and checkpoints. It did not render or invoke GUI, modify sources or create W/L. Older attempts and evidence remain available.

## Independent review

Codex read the scripts and claims, reran the worker verifier into a new directory, and freshly reran both native-evidence verifiers after worker completion. A focused read-only reviewer independently checked the joins, tabbed counts, geometry-pair calculation, input pins and candidate exclusions. No actionable P2/P3 finding remained for this bounded handoff.

- Worker verifier:34/34 checks pass in `attempt-05/codex-verify-01/verify-result.json`.
- Native verification:31 pages calibrated,769 frame maps,704 unique Formula/MCID groups, all25 previously missing-portion cases linked to actual glyph groups. Source/input/executable pins,221 tracked files and HEAD remain unchanged.
- The148 frames in51 tabbed paragraphs are all MathML; none is retained OLE. The65 retained OLE objects remain outside glyph-group screening.
- Fifteen candidate flags were reviewed; none establishes eligible natural overflow. The3 TQB intervals enter padding but not physical cell borders; the radical bbox flags were visually disposed of. No forced split or narrowed-region example was produced.
- All6 Hóa Bắc Ninh arrow cases Object73/76/92/94/98/104 were visually inspected in native PDF context on pages7/8/11. Their character boxes overhang their own frames by about2.21pt on the right, but no visible collision with adjacent formula/text was observed. They remain within the paragraph. `attempt-05/review/arrow-visual-review.json` pins the PDF and contact crop.

## Qualifications to worker terminology

“Glyph ink” fields in the inherited data mean PDF character bounding rectangles, not isolated solid-ink masks. The radical false positive demonstrates why that distinction matters. The new visual checks are visual dispositions, not pixel-mask proofs.

The173 “same-line” neighbour pairs are selected by positive vertical overlap of character-group rectangles. Native line identities agree wherever both portions are mapped;19 Hóa Bắc Ninh pairs lack native line corroboration. The measured minimum horizontal gap is25.041pt. This is a geometric neighbour screen, not proof of every native line identity.

The worker verifier checks reproducibility, pins, fixed totals and recorded outcomes. It does not independently establish source equivalence, universal geometry correctness or unrelated filesystem integrity. Codex's separate native/source/pin checks supply the stated independent evidence.

## Remaining work

No new W/L pair is justified by this study. An eligible pair still requires a genuine sidecar, a clean-importing W baseline and measured overflow within an actual region. Intended tab-column boundaries for148 frames, line-portion reconstruction for25 frames, vector-only paths/clipping, retained OLE glyph geometry and source semantics remain explicitly unresolved. Six pre-existing Formula error markers remain unchanged. FULL_END_ONLY, safety skips, the two Physics OLE at paragraph91 and prior INT limitations are unchanged.

The next investigation should establish a specific intended tab-column contract from source layout and actual native positions, or select a newly evidenced genuine overflow occurrence. It should not repeat the global screen or manufacture a split case. Corpus status remains needs_review; accepted is unchanged.

Primary handoff: `work/dsmt4-claude-region-overflow-20261113T201043/execution/continuation-05/report.md` and `review-handoff.json`. Codex review evidence: `attempt-05/review/`. The preceding Formula-group measurement report is `docs/working/codex_dsmt4_formula_group_review_2026-11-14.md`.
