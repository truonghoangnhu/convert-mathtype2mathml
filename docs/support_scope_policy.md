# Support Scope Policy

This is the canonical support boundary. It supersedes older statements that
DSMT4 investigations are frozen or outside the product roadmap.

## Supported inputs and verified decoding scope

- Modern `.docx` with native OMML equations.
- `.docx` containing legacy MathType OLE, including `Equation.DSMT4`, as
  **migration input** to MathML/OMML.
- DSMT4 support is conditional on the actual extracted MTEF payload and a
  verified decoder path. ProgID identifies the object, not its MTEF version,
  structure, formula contents, or conversion capability.
- A payload class is verified only for the structures covered by recorded
  real-source tests. A successful example does not establish support for all
  objects with that ProgID, MTEF version, or byte fingerprint.

## Canonical migration path

`OLE → extracted MTEF → normalized MathML → native OMML for Word`

In the measured corpus the MTEF that was decoded came from the copy MathType
embeds in the WMF preview of each object; the OLE BIN was parsed separately for
inventory and found byte-identical apart from one trailing byte in the WMF
(see [the corpus report](./dsmt4_real_corpus_2026-11-03.md)). Either copy is
MTEF; an image rendering of the preview is never a source of formula content.

Use the normalized MathML artifact to import an editable formula into
LibreOffice Math. Writer acceptance must verify the imported formula in its
actual document and after reopening. A preview image is reference evidence,
not an editable conversion. Existing native OMML remains on its current path.
The LibreOffice-only adapter investigated in the
[follow-up review](./working/codex_dsmt4_writer_mathml_review_2026-11-05.md)
now has a separate bounded W/L/T/G/C/I/B/D/A preparation command,
`scripts/transpect/prepare_libreoffice_mathml.py`. It writes a new MathML candidate,
keeps the source unchanged and reports `needs_review`, never application acceptance.
G only groups multiple children of `mfenced separators=""` for matched `()` or `||`,
with no attributes beyond `open`, `close`, `separators` and no significant mixed text.
It retains the original fence element and arguments. The 21 affected candidates
were rendered and reopened in a scoped Math/ODT probe; one absolute-value sample
also passed UI edit/save/close/reopen. See the
[follow-up evidence](./working/codex_dsmt4_ui_and_math_fences_2026-11-06.md).
Nonempty/default separators and other fences/attributes remain untested and unchanged.
C is limited to single ASCII-letter `mi` bases with `+`, `2+`, `3+` exponents; I to bare
comma-decimal `[a;b)` rows; B to a leading `|msub(mi,mi)|=...` row with single ASCII-letter operands. These repairs
cover another 13 rendered/reopened Math candidates. Unprobed exponents, attributes,
endpoints and operators remain outside the rules.
D only quotes the delimiter pair in adjacent `msup(mo "(", mo "°"), mi "C", mo ")"`
only in a single flat unstyled top-level math/mrow with one such unit, balanced
other bare parentheses and no other structural rule besides W; nested/styled
or combined contexts are deferred. D keeps the original script base/degree.
The [degree follow-up](./working/codex_dsmt4_degree_alignment_2026-11-06.md) records
production render and UI operand editing. Noncentered table alignment now has a
per-input diagnostic; its XML is retained and layout is not certified.
A handles only unstyled `math → mfenced(open={, close="", separators="") →
mtable(columnalign=left)` with exactly three flat rows/cells. Each row is a
single ASCII-letter lhs, equals, then integer/ASCII-letter terms with an optional
initial minus and binary plus/minus. An integer may have one following letter;
adjacent numbers/letters, chained relations, nested markup, mixed text, foreign
namespaces, metadata and unknown attributes do not receive A. The original
presentation tree stays intact; a generated `StarMath 5.0` annotation supplies
`alignl`. The measured importer treats annotation as authoritative, so the
restricted grammar and complete row comparison are required. Incoming metadata
is still kept byte-identical. Three actual candidates (toan013–015) passed the
recorded render/headless-roundtrip checks; toan015 has standalone Math UI
edit/reopen evidence with byte-identical production input. Other shapes, including
the nested toan016 table, retain diagnostics and need review. See the
[alignment evidence and limits](./working/codex_dsmt4_math_alignment_2026-11-06.md).
The F fence-expansion rule remains experimental and is not included.
Leading relations can fail on Writer DOCX roundtrips,
and Writer can lose left alignment within equation systems. Do not infer
DOCX compatibility from a successful Math/ODT example, or apply that adapter
to the normalized MathML used for Word.
The existing external transpect runtime decodes OLE/MTEF; this policy does not
claim a new general DSMT4 decoder or bundle that runtime into Maven.

## Failure and preservation contract

- `unsupported`: no verified usable decoder output, missing sidecar, empty or
  metadata-only MathML. Preserve original OLE, preview and placement.
- `failed`: conversion or transformation error. Preserve the original and
  report the reason; never substitute an empty formula.
- `needs_review`: candidate conversion exists but content, editing, placement
  or Word/Writer reopening has not been verified, or a placement safety check
  prevents patching. Retain the source document for comparison and recovery.
- An inline object immediately followed by a letter without an explicit text
  separator is retained with `INLINE_SPACING_REQUIRES_REVIEW`. The OLE viewport
  can supply a gap absent from MTEF and prose XML. The check includes mixed-run
  tails and crosses empty runs, bookmarks, proofing markers and rendered-page
  markers; it stops at real whitespace, tabs, breaks, punctuation or unhandled
  containers. It is a bounded guard, not a complete spacing detector. Multi-object
  paragraphs stay intact on a hit. No padding or formula characters are guessed.
  Retention is not editable migration acceptance: Writer can display the retained
  OLE incompletely even when Word preserves it. See the
  [inline-boundary evidence](./working/codex_dsmt4_inline_boundary_2026-11-06.md).
- Nonempty XML, a `<math/>`, nested empty containers, annotations, whitespace,
  or a preview alone cannot establish successful formula conversion.
- Current patch counters remain technical counters: `unresolved` and skip
  reasons are not evidence of content correctness. Diagnostic logs label
  unusable sidecars `unsupported` and transform exceptions `failed`.

Each newly converted inline OLE occupies one editable OMML `box` with `noBreak`
in the generated candidate, preserving its source object's indivisible boundary.
Display equations and original native OMML do not receive this wrapper. Word can
remove the explicit `noBreak` property on save while retaining the box; the
recorded Word probes still stayed together after reopening. This is scoped
evidence, not full pagination acceptance. An equation wider than the available
line needs separate layout review. Inline supplied OMML must be an `oMath` root,
or an `oMathPara` containing exactly one equation; unverified roots are refused
without mutating the source paragraph. See the
[noBreak follow-up](./working/codex_dsmt4_nobreak_2026-11-06.md).

## Acceptance

OMML normal-text runs containing letterlike/mathematical-alphanumeric symbols
outside verified conversion coverage are retained for review. The shared scope is
`src/main/resources/letterlike_policy.xml`; only ℝ/ℤ/ℕ/ℓ have been promoted from
pure `mtext` to math runs based on recorded Word roundtrips. This conservative
gate can retain otherwise usable unit symbols; it does not establish that every
symbol in those Unicode blocks is corrupted by Word. See the
[scope follow-up](./working/codex_dsmt4_symbol_scope_2026-11-06.md).

Counts are the first reconciliation check. Acceptance also requires correct
formula contents (including arrow direction, scripts, labels and conditions),
editable mathematical structure, original position and correct display after
saving and reopening in Word and Writer. Package/XML validation alone does
not prove application reopening or visual correctness.

Layout tolerance (owner decision, 2026-11-22). "Original position" means the
equation stays in its source paragraph, order and inline/display placement; it
does not mean the source pagination. Native OMML is shorter than the MathType
OLE preview it replaces (smaller inline fractions, tighter system rows), so
following content can move up and page breaks can differ from the source. No
hidden height structures (e.g. empty `m:phant` struts) are added to compensate.
A conversion is still unacceptable if any text, figure or equation is lost,
overlaps other content or runs past the margins. Word page counts against the
source must be measured and any exam that changes page count is listed; the
Writer measurement of 2026-11-22 found 166 → 160 pages over 32 exams. Evidence:
[layout decisions A6/B4](./working/claude_dsmt4_layout_decisions_2026-11-22.md).
Writer showing a sentence period alone on a line after an equation in Toán 02 is
a known display limitation.

Known presentation limitations (decision, 2026-11-22). In Word: a labelled ⇌ does
not stretch under its label; an empty-label MathType template arrow becomes a
plain short `→` (no substitution of `⟶`, which the MTEF does not contain);
`S.ABCD` shows a gap after the period; inline fractions and integrals render in
text style; Cambria Math replaces Times New Roman. These do not make an occurrence
`failed`, but they also do not satisfy display acceptance by themselves.

Writer route (decision, 2026-11-22). The required Writer acceptance route is the
normalized MathML imported into LibreOffice Math, as described above. Writer
opening the Word DOCX (OMML) must keep every formula's content, but its known
presentation defects are recorded as limitations rather than acceptance blockers:
labelled arrows drawn at script size, lost left alignment in equation systems, and
`¿` for a literal backslash such as the set difference `ℝ\{0}`. The last one is
still an open defect outside the 265-occurrence subset.

Start with the chemistry arrow formula, then reconcile every one of the
265 MathType occurrences across the five original exams. See
[the acceptance procedure](./dsmt4_migration_acceptance.md). The user-supplied
a3.1 review archive identifies the five exams; all 265 BIN occurrences match
the original sources byte-for-byte and in order in the archive's unshuffled
variants. See [the subset reconciliation](./working/dsmt4_five_exam_reconciliation_2026-11-05.md).
This closes identification and count reconciliation, not semantic or application acceptance.

Counting embedded objects is not patching them. Objects the patcher does not
walk (content controls, text boxes, other containers, headers, footers, notes)
are reported by container and kept unchanged; a reported object is not
thereby supported.

## Writer leading-temperature comparison boundary

The [2026-11-06 comparison repair](./working/codex_dsmt4_writer_comparison_2026-11-06.md)
groups the leading operator only for newly converted inline `>number°C` math
with the tested numeric-degree/unit structure. Its nonempty invisible delimiter
adds no operand or character. Word and Writer probes preserve the operator after
saving/reopening; this does not establish support for arbitrary leading relations,
full-exam layout or native/display-math changes. Corpus status remains `needs_review`.

## FULL_END_ONLY investigation

Continue investigating extracted payload boundaries, parser interpretation,
MTEF records and independent source evidence. Existing `FULL_END_ONLY` and
`UNSUPPORTED_SUBTYPE` labels are observed diagnostic classifications, not proof
that decoding is possible or intrinsically impossible. No production recovery
rule is justified yet. Do not generate a formula from a fingerprint or infer
content from counts. Keep these objects unchanged and report `unsupported`
until a faithful decoding path is demonstrated.

The prior [taxonomy](./dsmt4_taxonomy_baseline.md),
[MTEF semantics note](./dsmt4_mtef_spec_reference_note.md) and
[corpus audit](./dsmt4_full_in_corpus_audit_2026-04-23.md) remain evidence
snapshots. Their historical roadmap/freeze language is superseded here;
their recorded observations remain available for investigation.

## Out of scope

Direct binary `.doc` ingestion and malformed pseudo-DOCX packages. Resave
`.doc` to a valid `.docx` before migration, retaining the original for comparison.
Unverified broad legacy-format recovery is not a support promise.
