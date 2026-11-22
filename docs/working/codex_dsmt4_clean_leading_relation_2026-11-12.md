# Genuine sidecar leading-equals control after a clean prepared baseline

Scratch: `work/dsmt4-leading-relation-clean-2026-11-12/`. No production change, commit/push or corpus promotion. The preceding Claude rereview used session `2fdbb5a4-0d12-417c-a96c-304c0bdbdc80` and closed P2-1 at the evidence/reporting level and all P3, without claiming a converter fix. Its result is in `claude_dsmt4_mathml_authority_p2_rereview_2026-11-12.md`.

## Source and baseline gate

Tuyên Quang sidecar `6a301f808aa81f7401672938fb299bac2457c38ee5e63ccc71b442b98a742f88.wmf.mathml`, mapped by the existing manifest line202 to `/word/media/image282.wmf`, contains b=c=2,5 as five direct MathML children. Source bytes and SHA remain unchanged. This is existing sidecar provenance, not a new OLE/MTEF semantic audit. No preview/fingerprint reconstruction.

The untouched raw single form is **not** a clean baseline: system Writer imports its top-level siblings as five rows with two red error markers; Commands `b newline = newline c newline = newline 2,5`; saved presentation contains zero equals. That raw input was rejected for the wrapping baseline.

Existing `prepare()` rule **W only** wraps those children in one mrow. This prepared single form renders cleanly as one line b=c=2,5; Commands `{ b = c = 2,5 }`; saved presentation contains both equals. The baseline was rendered and visually inspected **before** building the wrapping variants. Unlike INT, this prepared baseline has no preexisting import failure. “Clean” here applies to this prepared import, not the untouched raw sidecar, mathematical/source certification, or GUI acceptance.

## Manual split, no input annotation

The cut was fixed before the second top-level equals (child index3, zero-based). Two mtable rows contain b=c and =2,5. Flattening the added row containers restores exactly the source subtree order/signatures. A second variant applies existing **L only**, inserting an empty mrow before the leading equals. Removing that one empty mrow yields exactly the raw split tree. Neither variant has an input annotation. No new rule, hand-authored StarMath, serializer, automatic breakpoint selection, or width inference was added.

Three pages compare the clean prepared baseline, raw split, and rule-L split. Both PDF and ODT are imported independently from the same MathML-only input with fresh profiles.

| Variant | Render / saved presentation | Importer-generated Commands |
|---|---|---|
| Prepared single baseline | b=c=2,5, one line; 2 equals | `{ b = c = 2,5 }` |
| Raw split | b=c then red ¿ and 2,5; 1 equals in saved presentation | `matrix{ { b = c } ## { = 2,5 } }` |
| Rule-L split | b=c then =2,5, two rows; 2 equals | `matrix{ { b = c } ## { { } = 2,5 } }` |

Thus the existing L empty operand prevents the measured leading-equals import failure on this one genuine, short sidecar after W gives a clean baseline. This does not establish a general mtable policy, left alignment, or long-formula wrapping fidelity. The raw Commands retaining an equals token are insufficient: the raw split still displays an error and its saved presentation loses that equals.

## Saved ODT reimport and verification

The first headless-saved ODT was copied byte-for-byte to a new scratch name and imported again with separate fresh headless PDF and ODT profiles. The generated annotations and presentation XML for all three objects are exactly the same in the first and second saved ODTs. Both rendered PDFs retain the same formula text lines and visible outcomes: raw split still fails, rule-L split still shows two rows and the leading equals. This is reimport of Writer-generated dual representations; it is **not** a second presentation-only import, actual GUI save-close-reopen, or an editability test.

All baseline pages and all three pages from both comparison PDFs were viewed individually as PNGs. Human observations are separate in `observations.json`. `verify_probe.py` checks source/input bytes, source subtree order, exact one-empty-mrow difference, W/L reports, absent input annotations/cached previews, exact baseline/split Commands, presentation equals counts, identical saved XML after the second import, and PDF formula lines. `verification-with-baselines.json` records the current full checks; earlier `verification.json` is retained. These checks and `git diff --check` pass.

Every renderer invocation uses `/Applications/LibreOffice.app/Contents/MacOS/soffice`, `LibreOffice 26.8.0.3 bce0998afefdbc355585ca324285661a2170ba77`. Exact binary/version/profile/argv/stdout/stderr are captured separately in each `*-run.json`; the bundled alpha is not used.

CUA again rejected Finder with “Computer Use was not approved to use Finder”. No new GUI acceptance is claimed and no user Word/Writer document was modified. Remaining work includes actual UI edit/save-close-reopen, presentation-only reimport if needed, larger nested shapes, tall/page-edge formulas and full-exam placement. Corpus stays needs_review, accepted promotions0, FULL_END_ONLY unsupported, safety skips unchanged.

## Claude review and P3 follow-up

Same-session review (`claude_dsmt4_clean_leading_relation_review_2026-11-12.md`) found no P1/P2 and three P3 about baseline byte linkage, profile preflight and dependency/mapping pinning. These were addressed in scratch after review; this follow-up is not a second Claude approval.

`dependencies-before-confirmed-runs.json` pins the prepared-baseline ODT, comparison input, current prepare() code, renderer helper and source manifest. This was captured **after** the original experiment, before the additional confirmed runs; it is not represented as an original-launch code pin. Baseline Object1 bytes are asserted identical to comparison page1 and the inspected prepared MathML. Manifest line202 is asserted exactly against image282.wmf and the sidecar path.

The original render helper used task-specific profile names but did not assert absence before launch. The helper now asserts that each profile does not exist, records that preflight, and refuses existing output directories. `validate_review_hardening.py` reran the same comparison input and its newly saved ODT with four explicitly checked fresh profiles, producing `confirmed-leading-*` and `confirmed-reimport-*` artifacts. All three saved formula XML byte strings match the original comparison, and all PDF text matches; dependency hashes remain unchanged across these reruns. `review-hardening-verification.json` records passing assertions. All six new PDF pages were individually viewed; `confirmed-observations.json` records the same visible outcomes. Original artifacts were retained.
