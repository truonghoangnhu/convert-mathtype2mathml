# DSMT4 — tab-boundary / line-portion partial review, 2026-11-14

Status: **partial worker checkpoint reviewed; requested handoff incomplete**. Same Claude session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80`, observed model `claude-fable-5-2`. Scratch only; no commit/push or accepted promotion.

## Worker progress and blocker

Attempt06 began the requested investigation with `--autocompact auto`, retained guards and the existing session/model. It made7 tool calls, wrote two checkpoints and retained two source references under `execution/continuation-06/`. It did not produce tab-boundary.json, line-portion-cases.json, a native probe, or a final report/verifier. No case is closed by this attempt.

The process exited1 with `is_error=true` despite a result subtype named success. The final rate event is rejected for the five-hour window, reset epoch1794681600: **2026-11-15 01:40 Asia/Ho_Chi_Minh** (2026-11-14 18:40 UTC). No retry loop, new session/model, overage change or automation was created.

## Independent findings

Codex reviewed the raw XML for each of the25 cases and independently reproduced the checkpoint's numerical evidence:

- 24 cases have no native SwParaPortion/FlyCnt data in the old dump. Their text frames have invalid size flags. The page-level pattern is consistent across all five dumps: portion data is present on pages1–2 and the first text frame of page3; later text frames lack it. A few earlier empty/no-portion frames with valid sizes remain distinguishable.
- Hóa Bắc Ninh Object22 has FlyCnt data. Its actual horizontal offset from the paragraph origin is7525 twips; summing the preceding raw portion widths yields7430. The difference is95 twips, or4.75pt. Raw line widths total10082 versus native line width10206, leaving124 twips of slack. The text after the tab has17 spaces before the object and5 afterward. Proportional allocation estimates4.7909pt before the object. This supports justification as the explanation, but is not an exact native spacing reconstruction. No tolerance was enlarged to force a match.

The worker read LibreOffice master source and inferred the missing portions were caused by the layout dump filter. Codex additionally fetched the filter at the **exact installed revision** `bce0998afefdbc355585ca324285661a2170ba77`. That revision contains the same relevant sequence: set a fixed visible area, invalidate content sizes, end the action, then dump. The source-version mismatch for this sequence is resolved. Source and hash: `attempt-06/codex-review-02/source-version-review.json` and `dumpfilter-installed-revision.cxx`; [official source at installed revision](https://raw.githubusercontent.com/LibreOffice/core/bce0998afefdbc355585ca324285661a2170ba77/sw/source/core/layout/dumpfilter.cxx).

This strengthens the filter-artifact hypothesis but does not prove its complete causal effect or recover the missing native portions. The checkpoint sentence “So the missing portions are a dump-tool artifact, not paragraph split/nesting” is stronger than the current control measurements support. Retain hypothesis status until a native control or alternate-position probe is calibrated. The proposed XTextViewCursor probe has not run and must not be reported as measured.

No tab-column bounds were newly established. The148 tabbed-frame /51 paragraph inventory remains the entry baseline. A tab stop is not automatically a column edge; configured stops, actual occupied segments and proven structural boundaries must remain separate.

## Scope and verification

The worker's source-download commands wrote seven `lo_*.cxx` temporary files under `/tmp`, outside its explicit scratch-only write root, then copied two references into scratch. These were diagnostic source downloads, not production/source-document changes. They are an operational scope deviation; the next prompt requires downloads, compiler outputs and temporary files under the new continuation directory. Existing `/tmp` files were not removed or overwritten by Codex.

Codex's read-only `attempt-06/review_checkpoint.py` passed when rerun into `attempt-06/codex-review-02/`: all25 cases classified,24 missing data, Object22 arithmetic reproduced,221 tracked files and HEAD unchanged. The first run encountered only a JSON serialization error while writing its new review directory; the script was corrected and rerun into a different new directory. Older evidence was not overwritten. No production integration, W/L pair or accepted increment was made.

## Next resume

The concrete continuation instructions are `attempt-06/next-resume.txt`. Keep the same session/model and normal auto compaction. First inspect the two worker checkpoints and Codex review; do not redo inventory or load large XML into the conversation. Prioritize a calibrated native probe and per-case records, then tab-boundary classification. Preserve unresolved status where native reconstruction or intended boundaries cannot be proved. Codex still owes review of the final worker handoff after it exists.
