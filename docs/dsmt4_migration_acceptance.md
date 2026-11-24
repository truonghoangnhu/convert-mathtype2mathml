# DSMT4 real-source acceptance

DSMT4 migration is active; verified decoding scope remains evidence-based.
This procedure implements [the support policy](./support_scope_policy.md).

## Final status (2026-11-24)

This is the closing snapshot for the 265 MathType occurrences in the five original
exams. Each occurrence is listed in the versioned
[265-row ledger](./acceptance/dsmt4-2026-11-24/ledger.csv); the
[snapshot index](./acceptance/dsmt4-2026-11-24/README.md) includes all 27 exceptions,
summary counts and source/output/runtime provenance. The original working ledger
remains at `work/dsmt4-claude-d-ledger-20261122/ledger.csv` locally.

- **accepted 238** (Hóa 95, Toán 112, TN 22, Lý 9), **needs_review 27**, failed 0,
  unsupported 0. Of the 27, 18 are retained OLE objects and 9 have a recorded
  presentation limitation; the list is in the D4 result below.
- **Output:** 247 occurrences are native OMML and 18 keep the source OLE. Writer
  document check after reopening: 241 pass, 6 known limitations, 18 retained OLE.
- **UI edit/save/reopen:** 17 samples on Word and 17 inside the Writer documents.
  Together they cover every structure group. hoa068 was also verified independently
  (2026-11-24).
- **Layout (Word, 29 exams):** 149 → 140 pages, 9 exams lose one page, none gains a
  page (B9). There are no overwide or inline-split equations in the four DSMT4
  exams (B7). Phantom height preservation is not used (B4). Matching MathType system
  row spacing (B10, optional) was closed without change on 2026-11-24.
- **Code:** merged to `main` through PRs #4 and #5 (review fixes P1/P2). The
  32-exam output regenerated at `12ed317` is identical to the A7 output.

Scope: acceptance covers these 265 occurrences only. Elsewhere in the 32-exam corpus,
converted equations remain `needs_review` and `FULL_END_ONLY` remains `unsupported`.
Sections dated before 2026-11-22 are kept as historical evidence. Statements there
that something is "open" or "pending" are superseded by this section.

## Evidence snapshot (2026-11-06, historical)

The expanded `in/` corpus now contains 32 DOCX files, 2,617 DSMT4 occurrences
and 27 native OMML equations. The external runtime has been installed locally.
Actual BIN MTEF parsing, sidecar generation and candidate patching have run;
see [the measured corpus report](./dsmt4_real_corpus_2026-11-03.md).

There are 2,286 OMML candidates and 331 retained MathType objects, including
one unsupported FULL_END_ONLY payload. All candidates remain `needs_review`.
Word and LibreOffice Math edit/save/reopen checks have been exercised for the
chemistry arrow, and Writer ODT save/reopen/render has been exercised. Exact
arrow/label layout and full-corpus semantic/application acceptance remain open.
The original 265-object / five-exam target is now an identified subset of
the 32-file inventory: the user supplied the a3.1 review ZIP on 2026-11-05.
All 265 original BIN occurrences match its unshuffled variants byte-for-byte
and in order. The subset has 247 inserted candidates and 18 retained OLE
objects, plus 18 preserved native OMML equations. See the
[per-object reconciliation](./working/dsmt4-history/dsmt4_five_exam_reconciliation_2026-11-05.md).
The archive's Word result fields are blank; application/semantic acceptance
is still open and cannot be inferred from these counts or hashes.
After placement, empty-script-base and inline-boundary safety fixes the candidates are 71 display and 2,215
inline equations. Standalone equations need explicit mathematical justification:
Word centres a lone inline `oMath` despite a left-aligned paragraph. Nine
indented object paragraphs are now retained pending placement review. See
[the follow-up evidence](./working/dsmt4-history/codex_dsmt4_word_placement_2026-11-04.md).
The later [prescript fix](./working/dsmt4-history/codex_dsmt4_prescript_order_2026-11-05.md)
corrects `sPre` child order and retains paragraphs containing empty script bases;
the [R1 guard](./working/dsmt4-history/codex_dsmt4_r1_2026-11-05.md) preserves OLE when invisible
paragraph artifacts would otherwise cause Word to centre a lone inline equation.
The [inline-boundary guard](./working/dsmt4-history/codex_dsmt4_inline_boundary_2026-11-06.md)
retains another 131 objects across 32 files, including 5 in the five-exam subset.
It preserves whole paragraphs instead of inferring spacing from an OLE viewport.
Word save/close/reopen was observed for li002/li010 on a separate copy; these are
retained OLE, not newly editable OMML. Writer shows incomplete glyphs in those
OLE both in source and output. No full application acceptance follows.

The [inline noBreak follow-up](./working/dsmt4-history/codex_dsmt4_nobreak_2026-11-06.md)
adds a box around each of the 2,215 newly converted inline equations; the latest
32-file output is `out/dsmt4-nobreak-final-2026-11-06/`. Counts and retained objects
are unchanged. A fresh Word baseline reproduced toan086 splitting across pages;
the grouped probe stayed together, including an in-equation edit/save/close/reopen.
Word removes the explicit `noBreak` property on save but retains the box.
The TN relation probe has not completed Word UI verification. Full pagination,
overwide equations and the per-application 265-occurrence ledger remain open;
no occurrence is promoted to accepted by these checks.

The full-exam acceptance run `dsmt4-acceptance-final-20261105T1448`
([report](./working/dsmt4-history/claude_dsmt4_acceptance_final_dsmt4-acceptance-final-20261105T1448.md))
records every one of the 265 occurrences against Word and Writer renders of the complete
exams and a LibreOffice Math import of all prepared candidates: accepted 0, needs_review 219,
failed 46. It found that Word saves ℝ/ℤ/ℕ/ℓ held in an `m:nor` run as plain letters; the
converter now emits letterlike-only `mtext` as an upright math run (local fix; Word UI
edit/save/reopen of the fixed output keeps ℝ and ℓ). UI edit/save/reopen was observed for 14 Word,
2 Writer DOCX and 2 LibreOffice Math/ODT samples only; a Writer DOCX save also drops `>` from
Hóa #68 and flattens labelled arrows. Other occurrences remain `not_run`.

Application evidence is scoped, not universal acceptance. The
[Writer/MathML review](./working/dsmt4-history/codex_dsmt4_writer_mathml_review_2026-11-05.md)
records editable ODT samples and the adapter investigation. The separate W/L/T/G/C/I/B
preparation command does not fix Writer's DOCX import/export failures for a leading
relation or its equation-row alignment. Word renders the current left-aligned
matrix rows correctly in the isolated Toán #15 probe, including after save/reopen;
this does not establish full-exam placement or editing acceptance.

The [2026-11-06 UI and fence follow-up](./working/dsmt4-history/codex_dsmt4_ui_and_math_fences_2026-11-06.md)
adds five isolated Writer DOCX edit/reopen checks, four isolated Math/ODT checks,
and full-document Writer UI saves for Lý, Toán and TN. G removes the demonstrated
fence-import defect in 21 Math candidates; C/I/B address 13 further Math import
failures. These checks do not certify page placement,
font, spacing or all remaining application roundtrips. The historical 265 ledger
is preserved; new evidence is a scoped overlay and accepted remains zero.

The [bounded alignment follow-up](./working/dsmt4-history/codex_dsmt4_math_alignment_2026-11-06.md)
adds rule A only to the separate LibreOffice Math adapter. Among the 265 Math
inputs, toan013–015 change and 262 remain byte-identical. Complete PDF row text,
left alignment and saved presentation match for the three changed cases.
toan015 also passed standalone Math UI edit/save/close/reopen; the production
input matches that probe byte-for-byte. This resolves the demonstrated isolated
Math row-alignment defect, without establishing Writer DOCX or full-exam layout.
The nested toan016 table remains unchanged with a diagnostic. Python now has
141 passing tests; Word candidate/retention counts and acceptance promotions
remain unchanged.

Operator-role integration (2026-11-22, A5–A7 of the
[completion checklist](./working/dsmt4_completion_checklist_2026-11-22.md)).
The converter now emits every explicit MathML `mo` as its own OMML run, so Writer
keeps it as an operator instead of literal text. It keeps same-property grouping
only for a two-token postfix charge in a superscript (`X^{2+}`, `M^{n+}`) and for
a whole fragment that is a leading `=` plus one number. The 32-exam native audit of
this converter found no new Writer error markers (10 → 10; the previous candidate's
4 `n+` markers are gone), 160/160 pages, and leaf text changes only where `bar` and
`Ni` are now read correctly. The latest output is
`out/dsmt4-a7-integration-20261122/corpus/`. Every package part matches the audited
candidate. Counts are unchanged: 71 display + 2,215 inline. The owner accepted the
resulting Writer reflow (A6) and chose no height phantoms (B4). See
[the layout decisions](./working/dsmt4-history/claude_dsmt4_layout_decisions_2026-11-22.md).
Accepted remains zero; the 265-occurrence ledger is rebuilt below.

Ledger rebuild on the final output (2026-11-22, C1–C3, D1/D3 of the checklist).
Writer DOCX now shows Hóa #68 `>150°C` correctly; labelled arrows and the Toán #15
system alignment remain Writer limitations. With the current preparation command all
265 MathML candidates import into LibreOffice Math without `¿`, and none of the 36
import failures of 2026-11-05 recurs. The output has 247 OMML and 18 retained OLE
occurrences (five more retained by the inline-spacing guard). The overlay ledger
records accepted 0, needs_review 265, failed 0 (previously 219/46): failures were
fixed or recorded as known limitations, not accepted. UI edit/save/reopen on this
output is `not_run`; Word page counts (B9), overwide equations (B7) and the per-group
UI checks (D2) still require an interactive Word session.

Word follow-up (2026-11-23). Word pages: 149 → 140 over 29 exams, nine exams one
page shorter, none longer. No equation in the four DSMT4 exams leaves the text
column or splits across lines. Word edit/save/reopen on the final output passed
for six chemistry samples (inline, table cell, left block, charges, labelled arrow,
leading relation); with the eleven Lý/TN/Toán samples (root, sPre, bevelled and plain
fractions, ℓ, vector, system, integral, prime, ℝ) all seventeen pass, and every other
equation in the four Word-saved copies keeps its content and structure. Word saves the
math minus as "-", the prime as "'" and ℓ as a script-style "l"; all still display as before.

Writer documents (2026-11-23). The four exams were opened in Writer with LibreOffice's
own MathType conversion off, so every DSMT4 object stayed an OLE frame in place; each
frame was matched byte-for-byte and by relationship ID to the source (265/265). The 247
occurrences converted to OMML for Word were replaced by LibreOffice Math objects holding
their prepared MathML; the 18 retained objects stayed OLE. In the documents, all 247
formulas equal a standalone import of the same MathML, are unchanged after a Writer save
and reopen (stable over a second cycle), remain as-character in the same paragraph, and
the text and frame order match the source conversion; Writer page count is unchanged
(18). A page-by-page review of the reopened render against the source found no content
error, overlap or margin overrun. Six occurrences show presentation limitations in
LibreOffice Math (three labelled arrows not stretched, two empty-label template arrows
drawn short, one bevelled fraction drawn stacked). Editing inside these Writer documents
(formula selected, edited in the Commands window, saved, closed, reopened) passed for
sixteen samples covering every structure group except the leading relation; the other
231 formulas were unchanged. The leading-relation sample (hoa068) passed on 2026-11-24
on a fresh copy of the Hóa document; the other 99 Hóa formulas were unchanged.

Independent verification (Codex, 2026-11-24). On a separate copy of
`out/dsmt4-claude-d4-writer-doc-20261123/verify/Hoa_Ha_Noi_L1-saved.odt`,
Object68 was selected through Writer's Navigator and opened in Commands. The
number was edited from `150` to `151`, preserving the leading relation:
`{ { } > 150 ^ ° "C" }` → `{ { } > 151 ^ ° "C" }`. After saving, closing and
reopening through the Writer UI, both Commands and the rendered formula still
showed `>151°C`. Inspection of the saved ODT confirmed that Object68 was the only
changed formula; the other 99 formula commands were unchanged, and its `as-char`
anchor and containing paragraph text were preserved. This independently confirms
the hoa068 edit/save/reopen result for Writer ODT with embedded LibreOffice Math;
it does not certify a Writer DOCX roundtrip or change the 238/27 ledger below.
Source/output hashes and observations are recorded in the
[independent verification report](./working/hoa068_independent_verification_2026-11-24.json).
The edited copy is a verification artifact, not a replacement for the exam output.

D4 result (2026-11-23). After a page-by-page review of the Word-saved and reopened copies
of all four exams, an occurrence is accepted when its output is native OMML, its Word
display after save and reopen was reviewed without a recorded limitation, its XML is
unchanged by the Word save, it passed the Writer document check after reopening, and its
structure group has a UI-verified sample on both Word and the Writer document. Ledger:
accepted 237 (Hóa 94, Toán 112, TN 22, Lý 9), needs_review 28, failed 0, unsupported 0;
after the hoa068 Writer sample (2026-11-24): accepted 238 (Hóa 95), needs_review 27.
Still needs_review: the 18 retained objects; hoa037, hoa042, hoa066, hoa067 and hoa086
(arrow presentation limitations); li009 (bevelled fraction drawn stacked in LibreOffice
Math); and toan022/027/090 (gap after the period in S.ABCD in Word). hoa068 was
needs_review until its leading-relation group got a Writer UI sample on 2026-11-24.

Review fixes after merge (2026-11-23, commit `12ed317`). Equation runs now carry the
source run's `w:vanish` (hidden text stays hidden), and a script base that holds only
empty or invisible runs, also inside `m:box`, is rejected as `missing_script_base` so the
OLE is kept. The 32-exam corpus regenerated with the JAR built at that commit is identical
to the A7 production output in every ZIP part
(`work/dsmt4-claude-p12-impact-20261123`), so the D4 ledger above is unchanged.

## Run order

1. Identify the exact chemistry arrow occurrence in its original exam and
   record the source document SHA-256, document part, paragraph/table/cell,
   relationship ID, OLE/preview part and SHA-256, and expected formula.
   Describe direction, reaction type, over/under labels, charge and subscripts.
2. Use `scripts/transpect/generate_sidecars.sh` with the original DOCX and
   external runtime (see README). Retain extracted OLE, MTEF bytes, parser
   trace, decoder version and normalized MathML. Classify by actual payload
   records using the audit below; ProgID alone is insufficient.
3. Compare MathML contents and structure against the source. An arrow's
   presence alone is insufficient if its labels or surrounding formula differ.
   A nonempty-content gate is necessary but does not validate equivalence.
4. Patch a separate DOCX using the manifest, preserving the original:

   ```bash
   java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
     --patch-docx in/chemistry.docx out/chemistry-omml.docx \
     --mathml-manifest work/chemistry/manifest.tsv
   ```

5. Open, edit, save and reopen the result in Word. Import normalized MathML
   into LibreOffice Math, place it in the corresponding Writer document,
   edit, save and reopen. Record exact application versions, output hashes,
   screenshots and observed results separately for each application.
6. Only after the arrow passes, repeat for all five original exams. Inventory
   all 265 occurrences, including duplicates, unsupported and failed cases.
   Group by MTEF payload class for decoding analysis while retaining each
   occurrence's position and acceptance record.

Existing payload audit (requires original sources and external runtime):

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --external-dir in/five-exams --format json > out/dsmt4-corpus-audit.json
```

This audit is diagnostic, not an application acceptance gate. Inspect actual
MTEF records, parser-stage errors and normalized MathML, and retain the output.
`FULL_END_ONLY` remains under investigation; no recovery is claimed.

## Per-occurrence acceptance record

Keep one record per source occurrence; repeated payloads still require placement
checks. Use explicit values `pass`, `fail`, `not_run` for the following checks:

| Field | Required evidence |
| --- | --- |
| Source and position | DOCX hash, part, paragraph/cell, relationship and occurrence IDs |
| Payload | OLE/preview hashes, extracted MTEF hash/version/records, decoder version |
| Classification | Actual payload class; `unknown` when extraction/parsing is unavailable |
| Formula | Expected content, MathML path/hash and reviewed content equivalence |
| Word | OMML output hash, edit/save/reopen, position and rendering checks |
| LibreOffice | Imported MathML, Writer output hash, edit/save/reopen and rendering checks |
| Preservation | Original OLE/preview and location retained on unsupported/failed cases |
| Result | `unsupported`, `failed`, `needs_review`, or `accepted` with evidence |

A generated candidate starts as `needs_review`. Mark `accepted` only when all
content, editability, placement and both application reopen checks pass.
Missing files/runtime/application evidence stay `not_run` / `needs_review`.
Reconcile accepted + unsupported + failed + needs_review against the measured
source inventory, and independently check the expected five files / 265 objects.

## Automated verification available here

- Java patch tests: reject empty, nested-empty, metadata-only, wrong-namespace
  and malformed sidecars; retain the original package byte-for-byte when no
  patch succeeds; retain OLE on transform errors and empty/bare-text OMML.
  Namespace-free MathML is normalized throughout the presentation tree before
  transforming to mathematical OMML runs.
- Shared sidecar-cache/manifest gate: visible presentation content is required;
  annotations, hidden phantom content and empty containers do not count, nor do
  tokens made only of controls, format characters or separators (Cc, Cf, Z*),
  CGJ or variation selectors. Visible base-plus-selector sequences are preserved.
  Java and Python use the same vectors
  (`fixtures/mathml_content/visible_content_vectors.json`).
- Placement, rollback and inventory tests: display equations only where explicit
  mathematical justification preserves the source placement (plain centred,
  left or right paragraphs); indents/numbering/bidi and ambiguous placement keep
  the OLE. Exact run/text order around split runs; a failure part-way
  leaves the live paragraph usable and unchanged, then patches, saves and
  reopens; objects outside the walked paragraphs are counted and kept.
- Modern OMML smoke/generated-output gates protect existing native equations.

These checks do not establish real MTEF decoding, semantic equivalence, visual
layout or successful editing/reopening in Word/Writer.

## Verification recorded for this change

Latest Writer comparison follow-up (2026-11-06): **116 Java tests** and generated-output
gate **4/4**, both freshly run; a fresh 32-file audit finds only Hóa #68's nonempty
operator grouping changed. Word full-copy and Writer minimal exact-structure UI
edit/save/close/reopen checks retain `>`; full-exam Writer saving was additionally
checked headlessly. These scopes do not establish full-layout or 265-occurrence
acceptance. Final independent Claude review hit its usage limit and is pending.
See the [bounded repair and evidence](./working/dsmt4-history/codex_dsmt4_writer_comparison_2026-11-06.md).

Previous noBreak/joint/alignment follow-up (2026-11-06): **114 Java / 141 Python / 4 workflow
tests**, generated-output gate 4/4, and a 32-file structural preservation audit.
The joint review adds a CDATA rejection regression for supplied inline roots;
fresh package contents match the noBreak output across all 32 files. The
[joint report](./working/dsmt4-history/codex_dsmt4_joint_followup_2026-11-06.md) also records TN
UI editing, source/output Word PDF pagination and a current occurrence mapping.
That mapping isolates historical verdicts; it is not a fresh 265-occurrence
application acceptance audit. The earlier boundary follow-up recorded 109 Java;
see the [boundary report](./working/dsmt4-history/codex_dsmt4_inline_boundary_2026-11-06.md).
The earlier symbol-scope follow-up recorded 101 Java / 116 Python tests and a packaged-JAR probe that exercises the
shared symbol policy with real mtext. The output comparison and Claude review
limits are recorded in the [symbol-scope follow-up](./working/dsmt4-history/codex_dsmt4_symbol_scope_2026-11-06.md).
The earlier figures below describe their original snapshots.

- 2026-11-22 operator-role integration: `mvn -o package` 150 Java tests passed,
  including 28 `OperatorBoundaryReviewTest` regressions (17 failed against the
  previous XSL). `python3 -m unittest discover -s tests` 144 passed, workflow 4
  passed, generated-output gate 4/4 (`out/dsmt4-a7-integration-20261122/modern-gate/`).
- `mvn -q -o package`: 95 Java tests passed after the letterlike-run fix of the
  acceptance run (93 at finalization, 92 before the
  additional invisible-nonspacing-control regression; 82 after initial placement work),
  including the real MathML→OMML transformer regression for namespace-free input.
- `python3 -m unittest discover -s tests`: 116 tests passed, including nine
  command-level LibreOffice preparation regressions. The openability-failure
  regression now owns its temporary manifest and report; it also passes when the
  default generated-output manifest is absent. It no longer reads or overwrites
  an existing `out/` run. The gate implementation remains unchanged.
- `python3 -m unittest discover -s scripts/workflow -p 'test_*.py'`: 4 passed.
- Modern smoke: 4 passed, 1 expected negative, 0 unexpected failures.
- Generated-output gate: 4/4 package and structural checks passed. This means
  ZIP/XML checks, not observed Word/Writer application reopening.
- The runtime and expanded real corpus have now been exercised; the measured
  report above separates parser/patch checks from application and layout
  acceptance. The full corpus remains unaccepted.

The [Celsius/alignment follow-up](./working/dsmt4-history/codex_dsmt4_degree_alignment_2026-11-06.md)
resolves the isolated Math tn022 degree-import defect, with UI editing273→274
and reopening on a QA copy. This raises scoped Math fixes to35/36; it does not
certify full-exam layout or lift other Word/Writer findings. toan015 alignment
remains failed. Historical ledgers and outputs are preserved.

Latest separate Math/closeout batch (2026-11-07): **143 Python tests passed**;
new V annotation changes only two of265 Math candidates and preserves prepared
presentation. Six standalone Math and one Writer/ODT embedded formula were
edited/saved/closed/reopened through UI. Fresh Writer renders of all5 exams
still show layout drift in the4 migrated exams; CN's4 pages are pixel-identical.
These are scoped checks, not complete application acceptance. See the
[closeout report](./working/dsmt4-history/codex_dsmt4_closeout_2026-11-07.md).

Independent Claude review completed after01:35 on2026-11-07: noP1/P2code
findings, one P2 evidence gap closed with7 current Math glyph/label/limit
render-save-reopen checks. Codex added boundary regressions; fresh118Java and
144Python tests pass. Full acceptance remains open. See the
[review resolution](./working/dsmt4-history/codex_dsmt4_claude_review_resolution_2026-11-07.md).
