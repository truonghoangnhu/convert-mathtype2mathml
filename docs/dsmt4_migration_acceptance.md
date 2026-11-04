# DSMT4 real-source acceptance

DSMT4 migration is active; verified decoding scope remains evidence-based.
This procedure implements [the support policy](./support_scope_policy.md).

## Current evidence (2026-11-03)

The expanded `in/` corpus now contains 32 DOCX files, 2,617 DSMT4 occurrences
and 27 native OMML equations. The external runtime has been installed locally.
Actual BIN MTEF parsing, sidecar generation and candidate patching have run;
see [the measured corpus report](./dsmt4_real_corpus_2026-11-03.md).

There are 2,508 OMML candidates and 109 retained MathType objects, including
one unsupported FULL_END_ONLY payload. All candidates remain `needs_review`.
Word and LibreOffice Math edit/save/reopen checks have been exercised for the
chemistry arrow, and Writer ODT save/reopen/render has been exercised. Exact
arrow/label layout and full-corpus semantic/application acceptance remain open.
The original 265-object / five-exam target is not substituted for the measured
32-file inventory or treated as a confirmed subset.

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
  annotations, hidden phantom content and empty containers do not count.
- Modern OMML smoke/generated-output gates protect existing native equations.

These checks do not establish real MTEF decoding, semantic equivalence, visual
layout or successful editing/reopening in Word/Writer.

## Verification recorded for this change

- `mvn -q test`: 64 Java tests passed, including the real MathML→OMML
  transformer regression for namespace-free input.
- `python3 -m unittest discover -s tests`: 104 tests passed after generating
  the modern output manifest. The existing
  `test_generated_output_gate_returns_openability_failure_before_structural_validation`
  depends on that artifact even though it mocks generation; it fails on a clean
  `out/` directory. No gate implementation/test was changed to hide this dependency.
- `python3 -m unittest discover -s scripts/workflow -p 'test_*.py'`: 4 passed.
- Modern smoke: 4 passed, 1 expected negative, 0 unexpected failures.
- Generated-output gate: 4/4 package and structural checks passed. This means
  ZIP/XML checks, not observed Word/Writer application reopening.
- The runtime and expanded real corpus have now been exercised; the measured
  report above separates parser/patch checks from application and layout
  acceptance. The full corpus remains unaccepted.
