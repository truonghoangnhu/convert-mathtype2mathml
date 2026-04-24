# docx-html-math

A practical pipeline for converting modern `.docx` documents while keeping equations on the native Word/OMML path.

Official support scope is now limited to modern `.docx` inputs with:

- native Word equations stored as **OMML**
- equation content that the current pipeline converts stably to **OMML**

Legacy DSMT4 / old MathType OLE material remains in this repository only as historical investigation and reporting context. It is no longer an active product target.

See also: [docs/support_scope_policy.md](./docs/support_scope_policy.md)
Technical checklist: [docs/modern_docx_omml_todo.md](./docs/modern_docx_omml_todo.md)

## Why this branch exists

The mainline path is a modern DOCX + OMML workflow:

- keep native OMML intact where it already exists
- preserve a canonical math representation that can round-trip through OMML cleanly
- keep the repository focused on stable `.docx` inputs instead of broad legacy format recovery

The repository still contains legacy investigation scripts and reports because they document past limits of old MathType / DSMT4 material, but those lines are frozen reference material rather than the active roadmap.

## Supported input scope

- modern `.docx` documents
- native OMML equations already stored in WordprocessingML
- equation content that the current pipeline converts stably to OMML
- HTML and DOCX flows that stay on the OMML-backed path

## Acceptance criteria

- equation count stays stable after round-trip through the supported pipeline
- equation placement stays stable in the reopened Word document
- block equations remain editable native OMML where the pipeline already supports them
- inline equations remain on the OMML-backed path without introducing legacy MathType/OLE regression
- multi-equation paragraphs stay readable and reopen safely in Word when they are already supported by the current pipeline
- supported output `.docx` keeps valid `m:oMath` / `m:oMathPara` structure for the equations it owns

## Out of scope

- legacy DSMT4 / old MathType OLE objects as an official product target
- old `.doc` equation workflows
- malformed or partially packaged pseudo-`.docx` files that fail normal DOCX package handling
- previously audited degenerate legacy equation families as active roadmap items

## Current project focus

- modern DOCX ingestion
- native OMML preservation and OMML-backed conversion
- predictable HTML output for modern documents
- stable DOCX output where the pipeline already converts equation content cleanly to OMML

## Current mainline pipeline focus

- preserve native OMML without forcing a legacy recovery path
- convert only equation content that already maps stably to OMML
- keep block equations, inline equations, and supported multi-equation paragraphs in the modern DOCX path
- treat legacy MathType/OLE recovery as historical context, not a target for new product work

## Regression expectations

- supported modern `.docx` inputs should keep equation count and placement stable
- reopened files should remain safe to edit in Word
- supported output should keep valid `oMath` / `oMathPara` structure
- diagnostics should clearly separate supported modern inputs from out-of-scope legacy or malformed packages
- smoke and regression runs should use the modern DOCX + OMML path as the baseline

## Migration guidance for legacy files

- Prefer reopening and resaving legacy material as modern `.docx` before using this repo.
- Prefer converting or recreating equations as native OMML in Word when possible.
- Treat old `.doc`, DSMT4, and MathType OLE-heavy sources as migration inputs, not as supported steady-state formats.
- If legacy files must be studied, use the frozen DSMT4 docs as historical reference only; do not treat them as the current roadmap.

## Non-goals

- Do not expand official support back to legacy DSMT4 / MathType OLE.
- Do not treat old `.doc` compatibility as part of the mainline product path.
- Do not open new legacy investigation or production-fix work from this policy update alone.
- Do not infer active support from historical audit scripts or archived reports.

## Repository layout

- `src/main/java/...` Java converter
- `src/main/resources/omml2mml.xsl` open-source OMML -> MathML stylesheet
- `src/main/resources/mml2omml.xsl` open-source MathML -> OMML stylesheet
- `scripts/transpect/generate_sidecars.sh` run transpect on extracted WMF/BIN files
- `scripts/transpect/run_docx_with_transpect.sh` end-to-end wrapper

Stable operational smoke gate: `python3 scripts/workflow/run_stable_pilot_smoke.py`

## Build the Java converter

Requirements:

- Java 17+
- Maven 3.9+

Build:

```bash
mvn package
```

This creates:

```text
target/docx-html-math-1.0.0-jar-with-dependencies.jar
```

## Run without transpect

For OMML-heavy documents:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar input.docx output.html
```

Optional: skip MathJax and emit plain HTML + MathML only:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar input.docx output.html --native-mathml-only
```

## Legacy sidecar workflow (historical reference only)

This section remains for historical and migration reference. It is not the official support boundary for the repository.

### 1) Prepare transpect prerequisites

Recommended layout for this repository:

```bash
git clone --recursive https://github.com/transpect/calabash-frontend.git tools/calabash
```

That single checkout already brings in:

- `xmlcalabash`
- `Saxon-HE`
- `transpect/mathtype-extension`
- the JRuby and Ruby gems needed by `mathtype-extension`

The scripts in `scripts/transpect/` are written to work with that layout on macOS and Linux.
They auto-detect the bundled JRuby/Ruby dependencies and, when `MT_DIR` points inside `tools/calabash/extensions/transpect`, they also auto-load `transpect-config.xml`.

Example variables:

```bash
export MT_DIR=$PWD/tools/calabash/extensions/transpect/mathtype-extension
export XMLCALABASH_JAR=$PWD/tools/calabash/distro/xmlcalabash-1.4.1-100.jar
export SAXON_HE_JAR=$PWD/tools/calabash/distro/lib/Saxon-HE-10.8.jar
```

### 2) Generate MathML sidecars from the DOCX package

```bash
./scripts/transpect/generate_sidecars.sh \
  input.docx \
  work/transpect \
  "$MT_DIR" \
  "$XMLCALABASH_JAR" \
  "$SAXON_HE_JAR"
```

This creates:

```text
work/transpect/manifest.tsv
work/transpect/mathml/*.mathml
```

The manifest maps original DOCX part names such as:

```text
/word/media/image12.wmf
/word/embeddings/oleObject3.bin
```

to generated MathML files.

### 3) Convert DOCX to HTML and consume the sidecars

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  input.docx \
  output.html \
  --mathml-manifest work/transpect/manifest.tsv
```

Or use the wrapper:

```bash
./scripts/transpect/run_docx_with_transpect.sh \
  input.docx \
  output.html \
  target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  "$MT_DIR" \
  "$XMLCALABASH_JAR" \
  "$SAXON_HE_JAR" \
  work/transpect
```

## What the Java converter does with the manifest

When it sees a relationship pointing to a package part like:

- `/word/media/*.wmf`
- `/word/embeddings/*.bin`

it checks whether that exact part name exists in `manifest.tsv`.

If a match exists:

- the converter injects the generated **MathML** into HTML
- MathJax renders it in the browser

The lookup is exact first and then falls back to a unique leaf-name match.
That makes the converter more tolerant when manifests use the same filenames but slightly different path prefixes.

If no match exists:

- it falls back to the image preview when possible
- otherwise it emits a visible placeholder

## DOCX patch mode

Officially supported use is the modern DOCX + OMML path. Legacy object patching details below are retained as historical implementation notes, not as the current support promise.

The HTML flow stays unchanged. The new mode adds a separate branch:

```text
DOCX -> DOCX(native OMML)
```

Current scope:

- native OMML is left untouched
- block equations are patched first
- standalone OLE/WMF equation paragraphs are the target shape
- safe inline equations are patched conservatively in phase 2
- phase 3A now patches a narrow tier of multi-object inline paragraphs
- phase 3.2 now allows a very narrow benign `lastRenderedPageBreak` artifact inside the same safe multi-object model
- phase 3.3 now allows a very narrow benign `drawing` artifact only when it appears as a standalone drawing-only run that does not disturb the text/object sequence
- phase 4 is benchmark-first only: expand corpus coverage, aggregate skip telemetry, and decide later whether any new patch phase is justified
- OLE binaries are never edited directly
- if a manifest entry cannot be resolved, the original object is kept and a warning is logged

Phase 2 inline limits:

- only `OLE_BIN` / `WMF_PREVIEW` occurrences with a manifest match are eligible
- the paragraph must not already contain native OMML
- the paragraph must contain exactly one object-math candidate
- the object must map cleanly to one run span
- paragraphs with multiple competing objects or ambiguous run content are skipped on purpose
- if safety checks fail, the original object is kept and the run is logged as skipped

Phase 3 multi-object tiers:

- tier 3A patches only multi-object paragraphs that can be planned left-to-right as a deterministic sequence of `TEXT` and `OBJECT` segments
- every object in the paragraph must resolve through the manifest and convert to OMML before any XML mutation starts
- native OMML, unknown sources, mixed object/text runs, multiple objects inside one run, and unsupported paragraph child structures are skipped on purpose
- the patch mutates the paragraph sequentially and rolls the whole paragraph back to a snapshot if any XML operation fails
- phase 3.2 keeps the same model but treats `lastRenderedPageBreak` as an ignorable layout artifact only when the run stays otherwise safe and deterministic after removing it
- phase 3.3 keeps the same model but treats `drawing` as ignorable only for standalone drawing-only runs; `drawing + object` or `drawing + text` in the same run are still skipped on purpose
- tier 3B is not enabled yet
- tier 3C remains skip-and-classify only for nested or ambiguous structures

Phase 3.1 classification and benchmark scope:

- no new patch heuristic is enabled in phase 3.1
- the patch path now classifies skip reasons with a stable taxonomy for benchmark use
- current taxonomy includes `NATIVE_OMML_PRESENT`, `DRAWING_IN_RUN`, `LAST_RENDERED_PAGE_BREAK_IN_RUN`, `MULTIPLE_OBJECTS_IN_SINGLE_RUN`, `MIXED_OBJECT_AND_TEXT_IN_RUN`, `UNSUPPORTED_PARAGRAPH_CHILD`, `UNKNOWN_SOURCE_KIND`, `AMBIGUOUS_SEGMENT_SEQUENCE`, `UNRESOLVED_MANIFEST`, `OMML_CONVERSION_FAILED`, `XML_MUTATION_ROLLBACK`, `OTHER_UNSAFE_MODEL`
- multi-object paragraph skips are counted once per paragraph
- unresolved single-object cases are counted at occurrence level because the patch path never entered a paragraph-level multi-object plan
- after phase 3.2, `LAST_RENDERED_PAGE_BREAK_IN_RUN` should only remain for cases that are still unsafe after ignoring the artifact; benign cases are patched instead of counted as skips
- after phase 3.3, `DRAWING_IN_RUN` should only remain for mixed or ambiguous drawing cases; standalone drawing-only artifact runs no longer block a safe multi-object paragraph

Phase 4 benchmark-first workflow:

- no new patch heuristic is enabled in phase 4
- the smoke runner now loads presets from `scripts/workflow/docx_patch_smoke_presets.json`
- the preset registry currently covers 11 benchmarkable DOCX + manifest pairs across `chemistry`, `math`, `physics`, and `mixed`
- larger inputs that do not yet have a manifest pair are intentionally left out of the preset registry until the corpus is benchmarkable end to end
- aggregate reporting now answers:
  - which presets still have residual skips
  - which skip reasons repeat across the selected corpus
  - how many presets are affected by each reason
  - whether the current corpus suggests `NO_ACTION`, `INVESTIGATE`, or `CONSIDER_PATCH`
- the automatic decision hint is intentionally narrow:
  - `NO_ACTION` when no residual skip reason remains across the selected presets
  - `CONSIDER_PATCH` only for structural patch-candidate reasons that affect at least 2 presets or reach a total count of at least 3 across the selected corpus
  - `INVESTIGATE` for smaller structural outliers, and also for manifest/conversion reliability buckets such as `UNRESOLVED_MANIFEST`, `OMML_CONVERSION_FAILED`, or `XML_MUTATION_ROLLBACK`
- representative-corpus impact is still a human decision on top of the runner output; the threshold is guidance for phase planning, not a hardcoded patch-engine rule

Run it with the same sidecar manifest:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  --patch-docx \
  input.docx \
  output.docx \
  --mathml-manifest work/transpect/manifest.tsv
```

Patch-docx logging:

- `--patch-log-level warnings` (default): summary + warning lines
- `--patch-log-level summary`: summary only, useful for coverage comparison across smoke runs
- summary format stays compact and now appends `multi_patched=... multi_skipped_unsafe=... multi_skipped_ambiguous=...`
- patch-docx output also prints a stable `Skip breakdown:` section with one line per taxonomy reason in enum order:

```text
Skip breakdown:
- DRAWING_IN_RUN=...
- LAST_RENDERED_PAGE_BREAK_IN_RUN=...
- ...
```

Patch path architecture:

- detect `NATIVE_OMML`, `OLE_BIN`, `WMF_PREVIEW`, `UNKNOWN`
- reuse manifest exact match first, then unique leaf-name fallback
- normalize sidecar MathML
- convert MathML -> OMML through `mml2omml.xsl` + Saxon
- inject OMML back into the DOCX for block-equation paragraphs
- for safe inline cases, reconstruct paragraph content around one object run and insert inline `oMath` at the same position
- for tier 3A multi-object cases, build a minimal paragraph plan from left to right and replace only the safe object runs in sequence

Manual smoke path:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  --patch-docx \
  in/Hoa_Ha_Tinh_L1.docx \
  out/Hoa_Ha_Tinh_L1-omml.docx \
  --mathml-manifest work/batches/convert-chem-no-leading-underscore-hoa-ha-tinh-l1-20260421-181615-03/Hoa_Ha_Tinh_L1/manifest.tsv
```

Multi-profile smoke runner:

```bash
python3 scripts/workflow/run_docx_patch_smoke.py \
  --preset chemistry-hatinh \
  --preset math-1202
```

List the current preset registry:

```bash
python3 scripts/workflow/run_docx_patch_smoke.py --list-presets
```

Run the full benchmarkable corpus:

```bash
python3 scripts/workflow/run_docx_patch_smoke.py --all-presets
```

Filter by subject:

```bash
python3 scripts/workflow/run_docx_patch_smoke.py \
  --all-presets \
  --subject math \
  --subject physics
```

Benchmark-friendly variants:

```bash
python3 scripts/workflow/run_docx_patch_smoke.py \
  --all-presets \
  --format tsv
```

```bash
python3 scripts/workflow/run_docx_patch_smoke.py \
  --all-presets \
  --format jsonl
```

Also available:

- `--preset <name>` for ad hoc subsets
- `--preset-config scripts/workflow/docx_patch_smoke_presets.json`
- `--subject chemistry|math|physics|mixed`
- `--patch-log-level summary|warnings`
- `--format text|jsonl|tsv`
- `--out-dir out/docx-patch-smoke`

The runner parses both `Patch summary:` and `Skip breakdown:` from the CLI output. It also enriches the report with additive reporting semantics from transpect `state.json` plus unresolved-manifest diagnostics when needed. `text` keeps the human-readable smoke view, while `jsonl` and `tsv` are intended for quick coverage diffing and phase-planning benchmarks.

Reporting semantics:

- `equation_scanned`
  - equation occurrences that should count toward patch-engine coverage
  - derived from `Patch summary.scanned`, then reduced only by embedded objects already classified upstream as non-equation
- `equation_patched`
  - equations newly patched by the engine (`block + inline`)
- `equation_native`
  - native OMML equations that were already present and therefore not a patch gap
- `equation_handled`
  - `equation_patched + equation_native`
- `equation_structural_residual_skips`
  - residual structural skip counts from the existing patch taxonomy such as `DRAWING_IN_RUN` or `MIXED_OBJECT_AND_TEXT_IN_RUN`
  - this is the number that matters when deciding whether to open a new patch-heuristic phase
- `unresolved_equation_upstream`
  - unresolved equation cases whose root cause lives in sidecar generation / transpect output rather than in the patch engine
- `non_equation_embedded_objects`
  - embedded objects classified upstream as not being equations
- `suppressed_non_equation_objects`
  - residual unresolved cases that are intentionally suppressed because they are non-equation embedded objects such as ChemSketch chemical diagrams

Per-preset output keeps the existing stable fields. The new aggregate section adds:

- total patch counts across selected presets
- equation coverage totals that exclude non-equation embedded objects from the equation denominator
- embedded-object diagnostics that stay visible without being mistaken for equation patch failures
- total skip counts per taxonomy reason
- diagnostic root causes for residual `UNRESOLVED_MANIFEST` cases
- number of presets affected by each reason
- top residual reasons across the selected corpus
- a final decision hint with a `focus` field

Example aggregate text footer:

```text
Aggregate summary:
  presets_total=11 presets_ok=11 presets_failed=0 presets_with_residual_skips=0
  Patch totals: scanned=... block=... inline=...
  Equation coverage: equation_scanned=... equation_patched=... equation_native=... equation_handled=... equation_structural_residual_skips=... unresolved_equation_upstream=... unresolved_equation_other=...
  Embedded object diagnostics: non_equation_embedded_objects=... suppressed_non_equation_objects=...
Aggregate skip breakdown:
  - DRAWING_IN_RUN=0 presets=0
  - LAST_RENDERED_PAGE_BREAK_IN_RUN=0 presets=0
  ...
Aggregate diagnostic root causes:
  - NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST=...
  - EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST=...
  ...
Top residual reasons:
  - none
Top diagnostic root causes:
  - none
Decision hint: NO_ACTION focus=NONE reason="no residual skip reasons observed across selected presets" threshold_presets=2 threshold_count=3 triggers=none diagnostic_triggers=none
```

Current aggregate semantics on the benchmark corpus are therefore easier to read correctly:

- the raw patch summary still reports `UNRESOLVED_MANIFEST=4`
- the semantic layer splits that into:
  - `unresolved_equation_upstream=2`
  - `suppressed_non_equation_objects=2`
- this makes it explicit that there are no residual equation structural skips in the current corpus, and that the remaining work is split between upstream equation conversion quality and non-equation embedded-object diagnostics

To add a new benchmark preset:

1. add one entry to `scripts/workflow/docx_patch_smoke_presets.json`
2. make sure both the input `.docx` and the matching `manifest.tsv` exist in the workspace
3. verify it appears in `--list-presets`
4. rerun `--all-presets` or a targeted subset

Unresolved manifest diagnostics:

```bash
python3 scripts/workflow/explain_unresolved_manifest.py \
  --preset chemistry-bac-ninh \
  --preset math-deso-11-tb
```

Also available:

- `--all-presets`
- `--format text|json`
- `--preset-config scripts/workflow/docx_patch_smoke_presets.json`

The unresolved explainer is investigation-only. It does not change patch heuristics. It audits:

- exact manifest hits vs unique leaf fallback candidates
- whether the referenced sidecar file exists and is usable MathML
- transpect workdir state such as `object_kind`, `bins_needed`, queued BIN converts, and manifest lineage
- repeated preview/object payload reuse that can fan one upstream issue out into multiple unresolved occurrences

Current observed residual root causes on the expanded corpus:

- `NON_EQUATION_OBJECT_SUPPRESSED_FROM_MANIFEST`
  - seen in `chemistry-bac-ninh`
  - the unresolved objects are `ACD.ChemSketch.20` with `object_kind=chemical-diagram`
  - transpect suppresses the shared preview and never queues the BIN payload for math conversion
  - this is not evidence of a manifest matching bug
- `EMPTY_GENERATED_SIDECAR_EXCLUDED_FROM_MANIFEST`
  - seen in `math-deso-11-tb`
  - both the shared WMF preview and the shared BIN payload generate `<math/>`, which the manifest builder treats as unusable and excludes
  - this points to transpect/output quality, not Java manifest lookup

Current investigation conclusion:

- no exact-match or unique leaf-fallback bug has been observed in the Java manifest lookup path for the remaining residual cases
- the chemistry residuals are corpus-side non-equation objects
- the math residuals are transpect-side empty MathML outputs
- the current investigation label is `INVESTIGATE_TRANSPECT_OUTPUT`, not `FIX_MATCHING_BUG`

Empty-generated-sidecar diagnostics:

```bash
python3 scripts/workflow/explain_empty_generated_sidecar.py \
  --preset math-deso-11-tb
```

Also available:

- `--format text|json`
- `--preset-config scripts/workflow/docx_patch_smoke_presets.json`

The empty-sidecar explainer is also investigation-only. It does not change DOCX patch heuristics or Java manifest lookup. It groups duplicate unresolved occurrences by BIN/preview digest and audits the transpect parser before MathML filtering:

- BIN payload digest and preview digest
- staged BIN/WMF input paths
- parser class, MTEF version, equation byte length, checksum
- top-level MTEF record sequence as parsed by the Ruby `mathtype` gem
- `eqn_prefs` counts plus the top-level tail after `eqn_prefs`
- whether the generated pre-MathML MTEF XML is metadata-only
- whether BIN and WMF resolve to the same effective extracted equation payload
- whether the evidence points to `UNSUPPORTED_OR_DEGENERATE_PAYLOAD`, `FIX_MTEF_TO_MATHML_STAGE`, `FIX_USABLE_SIDECAR_FILTER`, or `INVESTIGATE_TRANSPECT_CONVERTER`

Current finding for `math-deso-11-tb`:

- the two unresolved `Equation.DSMT4` occurrences collapse to one shared BIN digest plus one shared WMF digest reused twice
- both the BIN input and the WMF preview parse successfully, and both produce the same top-level record sequence:
  - `encoding_def`, four `font_def`, `eqn_prefs`, `full`, `end`
- both the BIN input and the WMF preview generate MTEF XML that only contains header/preferences metadata plus `<full/>` and `<end/>`
- neither side contains renderable body records such as `line`, `char`, or `tmpl`
- the extracted BIN equation payload is 193 bytes; the extracted WMF equation payload is the same 193-byte prefix plus one trailing `0x0A` byte after the end marker
- this means both BIN and WMF converge to the same effective MTEF payload; the WMF path only adds harmless trailing data after the parsed `end` record
- the downstream MathML output `<math/>` is therefore genuinely empty, so the usable-sidecar filter is behaving correctly when it excludes these sidecars from `manifest.tsv`
- the current decision for this case is `UNSUPPORTED_OR_DEGENERATE_PAYLOAD`

How to read the empty-sidecar output:

- `stage=PARSER_INPUT_PAYLOAD`
  - the parsed top-level MTEF payload itself ends before any renderable body record appears
  - this rules out a MathML-stage or usable-sidecar-filter bug for the inspected case
- `shared_prefix_bytes=... same_effective_payload=true`
  - BIN and WMF extract to the same effective payload, even if one source carries harmless trailing bytes after the parsed end marker
- `bin_tail=full,end` and `preview_tail=full,end`
  - after `eqn_prefs`, the parser sees only `FULL` and `END`; there is no `LINE`, `CHAR`, or `TMPL` content left to render

This diagnostic is upstream converter investigation, not a DOCX patch phase. It does not change patch heuristics, manifest lookup, or HTML rendering behavior.

EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY diagnostics:

```bash
python3 scripts/workflow/explain_empty_generated_sidecar_with_renderable_body.py \
  --extra-workdir work/dsmt4-external-audit/10-toan-hcm-2026--5c97b34e92a9 \
  --format text
```

Also available:

- `--format text|json`
- the same source-selection flags as `audit_dsmt4_corpus.py`

This helper is investigation-only. It does not change the DOCX patch engine, Java matching, the usable-sidecar filter, or default converter behavior.

Current reading for the known `10_Toan_HCM_2026` family:

- family label remains `INVESTIGATE_TRANSPECT_CONVERTER`
- parser pair remains `Mathtype::OleFileParser` / `Mathtype::WmfFileParser`
- current equation-bytes pair is `216/217`
- the parsed top-level record sequence is:
  - `mt_comment, encoding_def, font_def, font_def, font_def, font_def, eqn_prefs, full, end`
- the family still ends with `full -> end`
- no renderable math body records are visible before MathML generation
- the current best diagnosis is a converter/classification boundary around `mt_comment`, not a usable-sidecar filter bug
- do not open a production-fix branch unless a later investigation finds stable renderable math body evidence before MathML generation

DSMT4 corpus audit:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py --all-presets
```

Also available:

- `--preset <name>` to narrow the audit
- `--subject math|physics|chemistry|mixed`
- `--extra-workdir /abs/path/to/workdir`
- `--scan-path work/batches`
- `--external-docx /abs/path/to/file.docx`
- `--external-dir /abs/path/to/dir`
- `--prefer-underscore-first`
- `--external-work-root work/dsmt4-external-audit`
- `--format text|json|tsv`
- `--preset-config scripts/workflow/docx_patch_smoke_presets.json`

This script is benchmark/reporting only. It does not change DOCX patch heuristics, Java matching, or the usable-sidecar filter.

To combine the preset registry with extra corpus outside the registry:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --scan-path work/batches
```

To audit one external DOCX directly:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --external-docx /abs/path/to/_Toan_2026_Big.docx
```

To scan a directory of external DOCX files and process underscore-prefixed files first:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --all-presets \
  --external-dir /abs/path/to/docx-dir \
  --prefer-underscore-first
```

Or audit only an extra converted workdir without the registry:

```bash
python3 scripts/workflow/audit_dsmt4_corpus.py \
  --extra-workdir /abs/path/to/converted-workdir
```

When you pass `--external-docx` or `--external-dir`, the script will generate or reuse a sidecar workdir under `work/dsmt4-external-audit/` automatically. This is still audit-only: it stages sidecars and manifest data, but it does not change the DOCX patch engine.

What it reports:

- total DSMT4 occurrences, payload classes, and presets in scope
- registry vs external source totals
- external file totals for directly scanned DOCX inputs
- external payload classes that are genuinely new vs external payload classes that duplicate registry classes
- how many payload classes are reused across multiple occurrences
- how many payload classes are shared across multiple sources
- how many payload classes already prove renderable via a usable generated sidecar
- how many payload classes fall into metadata-only parser-stage patterns
- how many payload classes still need deeper converter-stage inspection
- taxonomy totals by stable `pattern_class`
- top combined pattern classes and top degenerate pattern classes
- top degenerate `pattern_signature` groups, including how many payload classes and source families collapse into each signature
- per-external-file summaries that show:
  - `dsmt4_occurrences`
  - `dsmt4_payload_classes`
  - `dsmt4_new_payload_classes_so_far`
  - `dsmt4_metadata_only_classes`
  - `full_end_only_present`
  - `top_pattern_classes`

How the DSMT4 corpus audit works:

- first, it groups `Equation.DSMT4` objects by payload class using `bin_hash + preview_hash`
- each payload class keeps a stable `pattern_signature` built from:
  - top-level record sequence
  - tail after `eqn_prefs`
  - top-level MTEF XML tags
  - parser class, equation byte length, and checksum
  - whether BIN/preview converge to the same effective payload
- classes with at least one usable generated sidecar are counted as `RENDERABLE_BODY_PRESENT`
- only classes with no usable sidecar are sent through the deeper JRuby/MTEF diagnostics
- those deep-audited classes are then classified as:
  - bucket-level compatibility classes:
    - `METADATA_ONLY_PAYLOAD`
    - `EMPTY_GENERATED_SIDECAR`
    - `OTHER_PARSER_PATTERN`
  - finer taxonomy `pattern_class` values:
    - `RENDERABLE_BODY_PRESENT`
    - `METADATA_ONLY_FULL_END_ONLY`
    - `METADATA_ONLY_NO_RENDERABLE_BODY_OTHER`
    - `EMPTY_GENERATED_SIDECAR_WITH_RENDERABLE_BODY`
    - `EMPTY_GENERATED_SIDECAR_WITH_METADATA_ONLY_MTEF`
    - `OTHER_PARSER_PATTERN`
    - `UNKNOWN_PATTERN`

How to confirm an unsupported/degenerate DSMT4 payload class:

- parser input is stable and parseable
- BIN and preview converge to the same effective payload, or to the same parser-stage shape
- the top-level payload consistently has no renderable body after `eqn_prefs`
- MTEF XML is consistently metadata-only
- the pattern repeats across more than one payload class or more than one preset

If only one payload class in one preset shows the metadata-only pattern, the audit reports `INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS` rather than over-claiming that the whole DSMT4 family is unsupported.

How to read the combined registry + external report:

- `dsmt4_external_sources_total`
  - how many external sources were actually audited outside the preset registry
- `external_files_scanned`
  - how many direct `--external-docx` / `--external-dir` files were staged and audited
- `dsmt4_external_payload_classes_total`
  - how many unique payload classes were seen in those external sources
- `dsmt4_external_new_payload_classes_total`
  - payload classes that do not exist anywhere in the registry corpus
- `dsmt4_external_existing_payload_classes_total`
  - payload classes that are only a second batch/source copy of registry classes
- `external_source_summaries`
  - use this section to decide which external file deserves deeper follow-up next
  - files with `dsmt4_new_payload_classes_so_far > 0` are the first priority
  - files with `full_end_only_present=true` are the first priority for deeper converter diagnostics
  - `top_pattern_classes` shows which taxonomy patterns dominate inside that file
- `top_pattern_classes`
  - combined ranking across registry plus external corpus by payload class count, then occurrence count
- `top_degenerate_pattern_classes`
  - same ranking, but excluding `RENDERABLE_BODY_PRESENT`
- `top_degenerate_pattern_signatures`
  - the strongest evidence for whether degenerate classes converge into one dominant parser-stage shape or multiple families
- `dsmt4_metadata_only_classes_total_combined`
  - unique metadata-only payload classes across registry plus external corpus combined
- `dsmt4_metadata_only_presets_total_combined`
  - affected registry presets only
- `dsmt4_metadata_only_sources_total_combined`
  - affected registry presets plus affected external sources

Decision label guidance:

- `INSUFFICIENT_EVIDENCE_NEED_MORE_CORPUS`
  - metadata-only/full-end-only still appears only in one payload class or one source family
- `CONFIRMED_UNSUPPORTED_OR_DEGENERATE_PAYLOAD_CLASS`
  - metadata-only/full-end-only repeats across multiple independent payload classes or multiple source families
- `INVESTIGATE_MTEF_TO_MATHML_STAGE`
  - parser-stage body content exists but generated sidecars still collapse to empty output
- `INVESTIGATE_PARSER_STAGE`
  - non-renderable payload classes remain but do not fit the known metadata-only pattern

This branch is audit/taxonomy only. It is not the branch to change DOCX patch heuristics, Java matching, the usable-sidecar filter, or converter logic.

Dominant FULL_END_ONLY family investigation:

```bash
python3 scripts/workflow/explain_dsmt4_full_end_only_family.py \
  --all-presets \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_Ly_2026_Big.docx
```

Also available:

- `--format text|json`
- `--report full|frozen-baseline`
- `--subtype-poc`
- the same source-selection flags as `audit_dsmt4_corpus.py`

This helper is still investigation-only. It narrows the already-audited corpus down to `METADATA_ONLY_FULL_END_ONLY` and answers whether the dominant degenerate family is one stable structural subtype or a messy collection of unrelated payloads.

This is an upstream parser-investigation branch, not a production-fix branch. It must not change DOCX patch heuristics, Java matching, the usable-sidecar filter, or default converter behavior.

What it reports:

- payload class count, occurrence count, and affected source families for the `METADATA_ONLY_FULL_END_ONLY` family
- structural subtaxonomy groups that ignore checksum noise and focus on parser-stage shape
- exact variants that keep checksum and byte-pair differences visible
- renderable-neighbor comparisons that show where the dominant family diverges from nearby renderable DSMT4 classes
- fingerprint candidates that rank possible subtype triggers before the top-level `full -> end` dispatch is finalized
- an optional subtype-specific POC summary gated by the exact `composite_pre_dispatch` trigger
- top-level dispatch probes around `full`, including record offsets, selected payload class, next record byte, and termination branch
- code-path probe notes that pin the split to the upstream parser record stream rather than the XML builder
- a primary investigation label:
  - `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
  - `UNSUPPORTED_SUBTYPE`
  - `READY_FOR_UPSTREAM_FIX_HYPOTHESIS`
- an evidence label:
  - `UNSUPPORTED_SUBTYPE`
  - `DEGENERATE_OR_CORRUPT_PAYLOAD`
  - `INSUFFICIENT_EVIDENCE`
- a stage label:
  - `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
  - `INVESTIGATE_MTEF_STRUCTURAL_DECODING`
  - `UNSUPPORTED_SUBTYPE`
- a fingerprint label:
  - `STRONG_PRE_DISPATCH_FINGERPRINT`
  - `WEAK_PRE_DISPATCH_FINGERPRINT`
  - `NO_USEFUL_FINGERPRINT`
- a subtype POC label when `--subtype-poc` is enabled:
  - `READY_FOR_UPSTREAM_FIX_HYPOTHESIS`
  - `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
  - `NO_ADDITIONAL_EVIDENCE_FROM_POC`
- a recommendation on whether to open a separate upstream investigation branch and which stage that branch should target

Current FULL_END_ONLY sub-taxonomy:

- `FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL`
  - same parser-stage record sequence
  - same `full,end` tail after `eqn_prefs`
  - same parser pair (`Mathtype::OleFileParser` / `Mathtype::WmfFileParser`)
  - BIN/WMF still converge to the same effective payload
- `FULL_END_ONLY_CANONICAL_193_194`
  - exact-variant bucket for the current observed canonical family where BIN/WMF byte lengths are `193/194`
- `FULL_END_ONLY_OTHER_STRUCTURAL_SIGNATURE`
  - reserved for future FULL_END_ONLY cases that do not match the canonical structure

How to read the final family label:

- `UNSUPPORTED_SUBTYPE`
  - the family is structurally stable across multiple independent classes/source families, so the evidence points to a real upstream subtype that the current parser/converter path does not materialize into renderable math
- `DEGENERATE_OR_CORRUPT_PAYLOAD`
  - the family does not stay structurally stable across independent cases, so corruption/noise is still the stronger explanation
- `INSUFFICIENT_EVIDENCE`
  - there is still not enough clean repeated evidence to justify a fix branch

How to read the structural diff with renderable neighbors:

- `eqn_prefs_successor=full/full`
  - both families still agree immediately after `eqn_prefs`
  - this tells you the real split is later
- `full_successor=end/slot`
  - this is the decisive parser-stage split for the dominant family investigated in this branch
  - the unresolved family goes `full -> end`, while the chosen renderable neighbor goes `full -> slot -> ...`
- `record_split=end/slot shared_prefix=7`
  - both classes share the same header/preferences prefix plus the `full` marker
  - the first meaningful top-level split is the byte after `full`
- `dispatch_after_full=end/slot dispatch_class=/Mathtype5::RecordLine`
  - the family side terminates because the next top-level byte is `0/end`
  - the neighbor side continues because the next top-level byte is `1/slot`, which `NamedRecord` dispatches into `RecordLine`
- `after_full_offsets=... after_full_bytes=0/1`
  - stream offsets and raw next-byte values for the decision point after `full`
- `bin_byte_diff=offset:... left:... right:...`
  - raw equation-byte window around the first differing byte between the dominant family and the chosen renderable neighbor
  - use this when the dispatch probe already shows `full -> end` vs `full -> slot -> ...` and you want byte-level confirmation that the split is already present before XML materialization
- if the raw parser-stage record stream already ends at `full,end` and the MTEF XML tags match that same structure, there is no evidence that later XML materialization is hiding body records
- that pattern supports `INVESTIGATE_PARSER_INPUT_INTERPRETATION` over `INVESTIGATE_MTEF_STRUCTURAL_DECODING`

How to run the fingerprint investigation:

```bash
python3 scripts/workflow/explain_dsmt4_full_end_only_family.py \
  --all-presets \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_Ly_2026_Big.docx \
  --format text
```

Use `--format json` when you want machine-diffable candidate details.

How to run the subtype-specific POC:

```bash
python3 scripts/workflow/explain_dsmt4_full_end_only_family.py \
  --all-presets \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_Ly_2026_Big.docx \
  --subtype-poc \
  --format text
```

This POC is still diagnostics-only. It does not change default parser/converter behavior. It only evaluates whether the exact `composite_pre_dispatch` subtype can be isolated cleanly and whether a gated post-`full` probe reveals any new parser-stage body evidence.

What the subtype-gated parser-input investigation now reports:

- `trigger_match=true|false`
  - whether the exact `composite_pre_dispatch` gate matched for that dominant/control entry
- `next_marker_byte_pair=[..., ...]`
  - the BIN/WMF marker byte seen immediately after `full`
- `dispatch_choice_pair=[..., ...]`
  - the BIN/WMF top-level dispatch choice immediately after `full`
- `termination_pair=[..., ...]`
  - whether the parser keeps reading into `slot` or terminates at `end`
- `pivot_label=...`
  - `NO_NEW_PIVOT_BEYOND_FIRST_RECORD_AFTER_FULL` when the gated subtype still goes straight to `end`
  - `ALTERNATE_BRANCH_VISIBLE` when a non-`end` branch such as `slot` is visible
  - `INCONCLUSIVE_INTERPRETIVE_PIVOT` when the gated trace is not uniform enough
- `new_interpretation_hypothesis=...`
  - the current best subtype-gated interpretation statement
  - if no new body/template evidence appears, this must explicitly stay in the "no new pivot/evidence" state

How to read the fingerprint ranking:

- `best_fingerprint=...`
  - the strongest candidate found across the currently selected dominant-family payload classes and their chosen renderable controls
- `coverage=x/y`
  - how many dominant-family payload classes share the same candidate value
- `false_positive_controls=x/y`
  - how many chosen renderable controls also match that candidate value
- `pre_dispatch=true`
  - the signal is available before the parser decides whether the marker after `full` is `end` or `slot`
- `brittle=true`
  - treat the candidate as exact-match support only, not as a robust subtype trigger

Fingerprint candidate types reported now:

- `equation_bytes_pair`
  - useful when the family consistently stays at `193/194` while controls do not
- `record_prefix_before_dispatch`
  - top-level record prefix up to and including `full`
- `eqn_prefs_shape`
  - counts inside `eqn_prefs`
  - useful only if it separates the family from controls; if controls share the same counts, it is not a trigger
- `effective_suffix_16`
  - strong supportive byte-level evidence around `full`, but not strictly pre-dispatch because the suffix already includes the terminal marker region
- `composite_pre_dispatch`
  - parser pair + same-effective-payload + equation-bytes pair + record prefix through `full` + `eqn_prefs` shape
  - this is the preferred candidate when it reaches full coverage with zero renderable-control false positives

Exact `composite_pre_dispatch` trigger used by the POC:

- parser pair = `Mathtype::OleFileParser` / `Mathtype::WmfFileParser`
- `same_effective_payload = true`
- `equation_bytes_pair = 193/194`
- `record_prefix_before_dispatch = encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full`
- `eqn_prefs_shape = 8/30/12`

The POC must not widen this trigger. If a control differs on any one of those fields, it must stay outside the subtype-gated path.

How to read the fingerprint label:

- `STRONG_PRE_DISPATCH_FINGERPRINT`
  - at least one non-brittle pre-dispatch candidate covers the whole dominant family and has zero false positives on the chosen renderable controls
- `WEAK_PRE_DISPATCH_FINGERPRINT`
  - some separating signal exists, but it is brittle, incomplete, or not strictly pre-dispatch
- `NO_USEFUL_FINGERPRINT`
  - nothing before dispatch cleanly separates the dominant family from the chosen controls

What a strong fingerprint means:

- it is enough to justify a narrowly-scoped upstream fix-investigation branch or POC trigger
- it is not enough by itself to merge a production fix
- this branch still remains investigation-only until the parser-side semantics are understood and the trigger survives a bounded regression corpus

How to read the subtype-specific POC result:

- `matched_family=x/y`
  - how many dominant-family payload classes hit the exact composite trigger
- `matched_controls=x/y`
  - chosen renderable controls that accidentally match the same trigger
  - this must stay at `0/y`
- `additional_parser_stage_evidence_count`
  - how many matched dominant classes reveal any new body/template evidence after the gated probe
- `controls_trace_preserved=true`
  - renderable controls stayed on their existing `full -> slot` trace
- `interpretive_pivot_summary`
  - aggregate pivot labels for the matched dominant family and the chosen renderable controls
  - this is where you check whether the investigation found any new pivot beyond `FIRST_RECORD_AFTER_FULL`
- `new_interpretation_hypothesis`
  - current subtype-gated hypothesis for parser-input interpretation
  - this must stay non-fix / non-production unless the gated probe reveals stable new parser-stage/body evidence

How to read the subtype POC label:

- `NO_ADDITIONAL_EVIDENCE_FROM_POC`
  - the trigger isolates the dominant family cleanly, but the gated probe still shows `full -> end` with no new body evidence
- `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
  - trigger isolation is not yet clean enough, or controls/family coverage are not yet stable enough for a subtype conclusion
- `READY_FOR_UPSTREAM_FIX_HYPOTHESIS`
  - only use this if the exact trigger isolates the family and the gated probe reveals stable new parser-stage evidence that can justify a separate production-fix branch

How to read the code-path probe:

- `records5/typesizes.rb`
  - `RecordFull` is an empty typesize marker, not a recursive container with its own branch payload
- `records5/mtef.rb`
  - `NamedRecord` dispatches purely by `record_type`
  - `Equation` keeps reading top-level records until it hits `record_type == 0`
- practical implication:
  - after `full`, the decisive event is the next top-level record byte
  - if the next byte is `0`, the parser legitimately reports `full -> end`
  - if the next byte is `1`, the parser continues into `slot`
- this means the current split is visible before `Converter.process` turns the snapshot into XML, so the XML builder is not the decision point

How to read the primary investigation label:

- `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
  - use this when the trace now localizes the split to the byte after `full`, but there is still no subtype-specific production fix ready
- `UNSUPPORTED_SUBTYPE`
  - use this when the family is clearly stable, but the split point is still not localized enough for a concrete next-stage investigation target
- `READY_FOR_UPSTREAM_FIX_HYPOTHESIS`
  - use this only after a safe probe produces a concrete subtype-specific decode rule and a bounded test corpus for a separate production-fix branch

This is an investigation branch for the dominant pattern family, not a patch/fix branch.

### Current DSMT4 investigation baseline

Historical baseline only. Use these notes as archived legacy reference, not as the active roadmap or official support scope.

Confirmed findings:

- residual DOCX-patch issues are not the blocker for this case
- dominant family = `FULL_END_ONLY_CANONICAL_NEAR_IDENTICAL`
- payload classes / occurrences / source families = `3 / 5 / 3`
- evidence label = `UNSUPPORTED_SUBTYPE`
- action label = `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
- fingerprint label = `STRONG_PRE_DISPATCH_FINGERPRINT`
- subtype POC label = `NO_ADDITIONAL_EVIDENCE_FROM_POC`
- decision point = `FIRST_RECORD_AFTER_FULL`
- decision point in code-path terms = `NamedRecord/Equation` top-level dispatch after `full`
- dominant family path = `full -> end`
- renderable controls path = `full -> slot -> ...`

Current trigger and controls:

- strongest trigger = `composite_pre_dispatch`
- canonical signature:
  - parser pair = `Mathtype::OleFileParser` / `Mathtype::WmfFileParser`
  - `same_effective_payload = true`
  - `equation_bytes_pair = 193/194`
  - `record_prefix_before_dispatch = encoding_def,font_def,font_def,font_def,font_def,eqn_prefs,full`
  - `eqn_prefs_shape = 8/30/12`
- current acceptance gate for any future upstream fix-investigation branch:
  - dominant family still matches `3/3`
  - false positives on chosen controls stay `0/3`
  - controls still preserve `full -> slot -> ...`
  - only accept a future change if new parser-stage/body evidence appears

Why no production fix yet:

- the current trace is strong enough to isolate a subtype and localize the useful decision point to the first record after `full`
- the subtype-gated POC still does not produce additional parser-stage/body evidence beyond the current `full -> end` trace
- this is not enough evidence to claim a decode rule, parser bug, or safe production fix

Current interpretation:

- this is currently best understood as an `UNSUPPORTED_SUBTYPE`
- the correct action remains `INVESTIGATE_PARSER_INPUT_INTERPRETATION`
- there is still not enough evidence to open a production-fix branch

Recommended next step:

- do not open a production-fix branch yet
- only reopen this line of work if at least one of the following appears:
  - new corpus showing stronger subtype diversity
  - new format/spec information for this subtype
  - new parser-stage/body evidence from a future targeted investigation
- until then, treat this branch as the frozen handoff baseline for the DSMT4 subtype investigation

Future revisit for the DSMT4 dominant subtype:

- current status is intentionally frozen
- reopen this only if at least one of the following appears:
  - new corpus
    - new independent DSMT4 source families
    - more payload classes matching the same dominant subtype
    - new neighboring classes that sharpen the split
  - new format/spec evidence
    - documentation for `full`, `slot`, or template/subobject semantics
    - any upstream reference clarifying whether `full -> end` can still be valid for a renderable subtype
  - new parser-stage evidence
    - a future probe that produces stable body/template evidence
    - a trace that shows a missed decode path after `full`
- acceptance gate before any future fix branch:
  - dominant family still matches `3/3`
  - chosen controls still have `0/3` false positives
  - controls still preserve `full -> slot -> ...`
  - new investigation produces additional parser-stage/body evidence
  - any proposed fix can be scoped narrowly enough to avoid regressions
- preferred next branch, if work resumes:
  - `spec/reference investigation`
  - `new corpus expansion`
  - do not jump directly to a production parser fix

Explicit non-goals for this branch:

- do not open a production fix
- do not change the DOCX patch engine
- do not change the Java matching path
- do not change the usable-sidecar filter
- do not change default parser/converter behavior
- do not assert that `full -> end` is definitively a parser bug
- do not merge a decode rule without new parser-stage/body evidence

Handoff helper:

```bash
python3 scripts/workflow/explain_dsmt4_full_end_only_family.py \
  --all-presets \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_Ly_2026_Big.docx \
  --subtype-poc \
  --report frozen-baseline \
  --format text
```

JSON form:

```bash
python3 scripts/workflow/explain_dsmt4_full_end_only_family.py \
  --all-presets \
  --external-docx in/_Toan_2026_Big.docx \
  --external-docx in/_Ly_2026_Big.docx \
  --subtype-poc \
  --report frozen-baseline \
  --format json
```

## CLI options

```text
java -jar ... <input.docx> <output.html> [--native-mathml-only] [--mathml-manifest manifest.tsv] [--subject ...] [--output-mode internal|publish]
java -jar ... --patch-docx <input.docx> <output.docx> [--mathml-manifest manifest.tsv] [--patch-log-level summary|warnings]
```

`--output-mode` behavior:

- `publish` (default): apply final publish sanitization (strip debug leakage, publish-clean output)
- `internal`: keep richer internal/debug/provenance details for QA/dev analysis

## QA publish gates

Run QA with explicit mode:

```bash
python3 scripts/qa/audit_exam_bundle.py output.html \
  --asset-dir output_files \
  --subject math \
  --output-mode publish \
  --json-out qa.json \
  --md-out qa.md
```

Gate severities:

- `info`
- `warning`
- `error`
- `blocker`

Verdict mapping:

- any blocker -> `blocked`
- else any warning/error -> `needs_review`
- otherwise -> `safe_to_publish`

## Output contract artifacts (Phase A)

Batch conversion now also emits deterministic JSON contract files per input:

- `manifest.json`
- `exam_bundle.json`
- `question_bank_items.json`
- `qa.json`

Contract generator entrypoint:

```bash
python3 scripts/contracts/generate_output_contract.py \
  --html out/<run>/html/<file>-transpect.html \
  --qa-json out/<run>/qa/<file>.qa.json \
  --source-docx in/<file>.docx \
  --subject math \
  --output-mode publish \
  --out-dir out/<run>/contracts/<file>
```

See:

- `docs/output_contract_v1.md`
- `docs/publish_gates_matrix.md`
- `docs/parser_report_v1.md`
- `docs/performance_baseline_v1.md`

## Phase B regression + baseline runner

Run the fixed Phase B regression set (2 chemistry, 2 physics, 2 math, 1 hard OLE, 1 OMML-clean)
and generate timing baseline + parser outputs:

```bash
python3 scripts/regression/run_phase_b_regression.py \
  --inventory regression_set/phase_b_inventory.json \
  --output-mode publish
```

This emits:

- `out/<run-name>/regression-sample-inventory.json`
- `out/<run-name>/baseline/performance-baseline.json`
- `out/<run-name>/baseline/performance-baseline.md`
- per-sample artifacts under `out/<run-name>/samples/<sample_id>/...`

## Phase C docs and override policy

Phase C adds documentation-first governance for core promotion, controlled edge-case overrides,
and DOCX export direction.

See:

- `docs/core-promotion/README.md`
- `docs/core-promotion/candidate_registry.md`
- `docs/override_manifest_v1.md`
- `docs/docx_export_direction_v1.md`

Working notes, internal specs, and active planning documents are grouped under:

- `docs/working/README.md`

Override manifest example and validator:

```bash
python3 scripts/overrides/validate_override_manifest.py \
  --manifest overrides/override_manifest.example.json
```

## Important scope note

Official support direction is now:

- modern `.docx`
- native OMML first
- only equation formats that the current pipeline converts stably to OMML

Historical legacy context in this branch still includes:

- **OMML** -> handled directly in Java
- **MathType WMF/OLE** -> handled by transpect outside Java, then fed back as sidecars

Legacy MathType/DSMT4 material is retained for reference and migration context only. It is not the current product target.

The repository does **not** attempt to embed the full transpect stack into Maven.
That keeps the core Java project cleaner and makes troubleshooting easier.

The external runtime is expected to live under `tools/calabash/` for a reproducible local setup.

## Output structure

If you write to:

```text
report.html
```

the converter also creates:

```text
report_files/
```

for ordinary extracted images and any remaining OLE preview images.

## Included third-party resource

This project bundles `src/main/resources/omml2mml.xsl` from `transpect/docx2hub`.
See `LICENSE_transpect_docx2hub.txt`.
