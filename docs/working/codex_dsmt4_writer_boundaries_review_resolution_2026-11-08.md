# Codex response to the Writer boundary review

The Claude review completed successfully in the existing read-only session. No P1 was reported. The review snapshot is retained unchanged at `claude_dsmt4_writer_boundaries_review_2026-11-08.md`.

## Findings checked

- **P2-1 open:** no common spacing value has been validated across Word and Writer.191/103 and178/96 remain local measurements. No converter change.
- **P2-2 partly resolved:** the three new trials were actually authored in Writer at the calibrated paragraph, saved, closed and reopened. This removes the whole-Word-oMath replacement confound for those trials. However Writer removes the original outer box (1→0), so the suggested assertion that it survives is contradicted by the observed export. Report the normalization rather than restoring or pretending to preserve it. Numerical baseline residuals after the UI edits were not measured.
- **P2-3: basic Word open-only comparison completed; roundtrip/measurement limits remain open:** Word shows six-term formula intact on a new line, boxed nine-term clipping, unboxed nine-term operator wrapping with final term/fence visible, and edge question+answers together on page1. Evidence: `word-open-observations.json` and four target screenshots. This is not edit/save/reopen or a measured layout pass. Writer no-box still clips, so global box removal is not justified.
- **P3-3 strengthened:** `verify_growth.py` now locates the first math's ancestor paragraph and verifies paragraph2=Câu1, paragraph3=answers before checking178/96. The old “last two before values” assertion was insufficient. New output uses a new filename; original evidence is preserved. Reproducible provenance of the Word calibration sample remains missing.
- **P3-7 updated:** narrative reports/checkpoints now point to the completed Claude review. Historical raw credit-error results and original review snapshot are retained.
- Other P3 gaps remain open: page-top spacing suppression, reverse cross-app symbol rendering, contextual/style/preceding-spacing effects, and numeric-run property differences in deterministic probes.

## New UI evidence

`work/dsmt4-layout-boundaries-2026-11-08/ui-roundtrip-verification.json` records115maths/file, only math1 changed in joined text, joined prose preserved, correct target paragraph8 (edge9), before191/103 and box removal. Screenshots show full fractions and six-term expression after reopen. The page-edge question and answers remain split across pages. This is local evidence only; neither box preservation nor whole-document fidelity is asserted.

Writer crashed during one long-expression attempt, recovery was observed, and a later retry succeeded. Crash cause is unknown. The nine-term overflow is still a synthetic growth limitation, not an established converter defect. keepNext remains a rejected position-changing control.

No production code changed, no acceptance promotion, no commit/push. Corpus needs_review, FULL_END_ONLY unsupported, original safety skips and Lý¶91 retained.

## Follow-up review and additional checks

Claude's completed follow-up `claude_dsmt4_writer_ui_followup_review_2026-11-08.md` found no new P1/P2 in the verifier/report and accepted only the Writer-authored resolution of P2-2. Its P2-3 statement predates the Word observations now recorded above.

Codex addressed its small evidence gaps as follows:

- Counted outer boxes across all115maths: baseline110, each of3UI exports0; each of4headless save/reopens110→0. File-wide within these samples; no general claim beyond them.
- Rendered the3UI-saved files in fresh Writer profiles. All4pages; cited Câu1/formula/answer text bounds match earlier diagnostics, visual regions inspected. Status-bar counts are not used.
- Opened all3Writer UI-saved files in Word: complete local content, but unboxed six-term formula breaks inside the expression and page-edge grouping differs from Writer.
- Relabeled UI metadata as manual observations. Strengthened Writer growth verifier to bind the edited formula to its baseline ancestor paragraph, with Câu1 explicit for math1. Missing spacing yields assertion rather than AttributeError. Both verifiers pass.
- Recorded that after crash recovery the successful wrap retry reopened the on-disk file and verified original `(u_n)` Commands before editing. Crash cause remains unknown.
- Updated stale “blocked interactive trials” wording. Preserved raw review snapshots and outputs.

The missing pre-edit package hashes and reproducible Word calibration provenance remain acknowledged gaps. P2-1 common spacing/context evidence remains open. The boundary comparison closes the basic Word-rendering omission, while larger Word edits/save/reopens and cross-application consequences are still limited. No converter policy changed.

## Final boundary review

Claude completed `claude_dsmt4_boundary_closeout_review_2026-11-09.md`: no P1/P2 errors in the new evidence; basic missing Word rendering is closed, while common spacing and larger Word roundtrips remain open. Codex recorded the installed Word version/build and125%zoom in `word-open-observations.json`, fixed the P2-3 heading, and checked all3UI DOCX hashes against the initial verifier output captured before Word viewing: unchanged. Deterministic-probe pre-view hashes were not recorded, so current hashes alone do not close that provenance gap. No Word edit/save was performed intentionally, and no hash proof is claimed for those4inputs. New evidence: `word-view-hash-verification.json` and `ui-vs-diagnostic-labels.json`.
