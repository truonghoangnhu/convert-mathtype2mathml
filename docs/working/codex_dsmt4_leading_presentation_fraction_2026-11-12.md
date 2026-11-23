# Leading equals: presentation-only reimport and a fraction sidecar

Scratch: `work/dsmt4-leading-presentation-2026-11-12/`. No production changes, commit/push or accepted promotion. Same Claude session rereview closed all three P3 from the previous experiment; see `claude_dsmt4_clean_leading_p3_rereview_2026-11-12.md`. Its optional current-prepare determinism check is now included and passes for both previous scalar artifacts.

## Saved scalar MathML without annotation

The saved raw and prepared split objects from the confirmed b=c=2,5 run were embedded into a new ODT as annotated and presentation-only pairs. Each stripped variant differs only by deleting its annotation element, with exact tree/byte checks. No prepare() was reapplied to saved MathML. The source saved ODT hash, source sidecar hash and new input hashes are pinned in `presentation-plan.json`.

| Saved scalar input | New render | Equals in new saved presentation |
|---|---|---|
| Prepared split, annotated | b=c then =2,5, clean | 2 |
| Prepared split, annotation removed | b=c then =2,5, clean | 2 |
| Raw split, annotated | b=c then red ¿ and 2,5 | 1 |
| Raw split, annotation removed | b=c then 2,5, no red error but missing equals | 1 |

The prepared pair produces byte-identical saved formula content.xml, including Commands `matrix{ { b = c } ## { { } = 2,5 } }`. Extracted PDF formula glyph origins/font sizes also match. This is a measured presentation-only reimport success for the scalar leading equals, distinct from reimporting a dual representation.

The negative control demonstrates why a clean-looking render is insufficient: raw Writer-saved presentation had already lost the second equals; deleting annotation removes the red relation error but cannot restore that token. Its regenerated Commands are `matrix{ { b = c } ## { { } 2,5 } }`. It is not a corrected output and must not be accepted.

## Second genuine sidecar with stacked fractions

Tuyên Quang sidecar `87d193454a386e7e3cea341aa407192edd6901bb9c40b17becd7e22f055dae15.wmf.mathml` contains P=72/720=1/10 with two mfrac subtrees. The existing manifest mapping, source bytes, prepare() code and renderer helper were pinned before import (`fraction-plan.json`); mapping/hashes are checked again by the verifier. This is existing sidecar provenance, not a fresh OLE/MTEF semantic audit or reconstruction from flattened tokens/preview.

Existing W only gives a clean one-line baseline, visually inspected before split construction. Saved Commands are `{ P = { frac { 72 } { 720 } } = { frac { 1 } { 10 } } }`, with two equals and two exact source fraction subtree signatures. The baseline input Object1 is byte-identical to comparison page1. The builder gates on saved Commands, fraction/equals counts, source/input hashes, and a separate named human observation record.

A manual split before child3 (second top-level equals) yields P=72/720 on row1 and =1/10 on row2. Raw split fails: red relation marker and only one equals in saved presentation. Existing L only adds one empty mrow before the leading equals and renders both rows cleanly with two equals. All source subtree signatures/order are retained by construction; removing exactly that added empty mrow restores the raw split tree. Both fractions remain structurally identical to the source in the saved outputs. No automatic break selection or width inference is involved; this short formula already fits the synthetic column.

The saved fraction baseline and saved L split were then reimported as annotated/presentation-only pairs in a separate four-page ODT. No prepare() or hand-authored annotation was applied to them. For each pair, both new saved content.xml bytes and importer-generated Commands are identical. Both retain two equals and the stacked fractions; the split pair retains the empty operand before row2 equals. Extracted formula glyph origins/font sizes match between each annotated/stripped pair. All four pages were individually viewed, with no visible red error marker. This does not certify semantic equivalence of arbitrary Writer exports.

## Verification and limits

`verify_probe.py` passes: exact annotation deletion; source/manifest/code/input hashes; baseline byte linkage; source fraction subtrees and order; one-empty-mrow L difference; deterministic prepare() reproduction of current and prior prepared artifacts; exact positive-pair saved XML; negative-control equals loss; PDF text/glyph-origin checks; version and prelaunch profile-absence assertions. `verification.json` records the results. Human visual observations are stored separately; all 12 newly rendered pages were viewed individually. `git diff --check` passes.

Every run uses `/Applications/LibreOffice.app/Contents/MacOS/soffice`, LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77, with separate profiles asserted absent before launch; exact command/profile/version/stdout/stderr in each `*-run.json`. The bundled alpha is not used. No new GUI attempt was made this turn; the preceding CUA Finder permission blocker is unchanged in the available evidence. These are headless import/save/reimport observations, not GUI edit/save-close-reopen or editability acceptance.

Scope remains two short genuine sidecars and manual cuts. No general mtable/left-alignment policy, serializer/generator, long-formula wrapping, tall/page-edge/full-exam fidelity, DOCX/Word route, or source semantic acceptance follows. INT remains unresolved, FULL_END_ONLY unsupported, safety skips unchanged; corpus stays needs_review, accepted promotions0.

## Same-session review follow-up

Claude review (`claude_dsmt4_leading_presentation_fraction_review_2026-11-12.md`) found no P1/P2 and one P3 requesting explicit machine checks for ¿ absence on all positive fraction pages and source fraction signatures on all four fraction-presentation outputs. Those assertions are now added and pass without rerendering. The latest record is `verification-p3.json`; the original `verification.json` is retained. Visual “no visible red marker” observations remain independently human-recorded, since absence of an extracted ¿ alone cannot establish absence of every rendering defect. This P3 follow-up has not had a second Claude approval.
