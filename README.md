# docx-html-math (transpect branch for many MathType WMF files)

A practical pipeline for converting `.docx` to HTML while keeping equations renderable on the web.

This branch combines two strategies:

1. **Apache POI + Saxon-HE** for the stable path:
   - regular text and tables
   - normal images
   - native Word equations stored as **OMML**
2. **transpect mathtype-extension** for the difficult path:
   - MathType equations stored as **WMF previews** and/or **OLE `.bin` objects**
   - external conversion to **MathML sidecars**
   - final HTML renders the MathML with **MathJax**

This repo now also contains a parallel MVP path for patching legacy math objects back into native Word math:

3. **DOCX patch mode** for Word-native output:
   - consume the same `manifest.tsv` + sidecar `*.mathml`
   - convert MathML to **OMML**
   - write a new `.docx` with native Word equations for block-math cases

## Why this branch exists

For documents that contain many legacy MathType equations, a POI-only converter usually falls back to preview images.
This branch adds a second stage:

- first generate **MathML sidecars** from `/word/media/*.wmf` and `/word/embeddings/*.bin`
- then let the Java converter replace matching DOCX assets with real MathML

That keeps the final HTML semantic and web-friendly.

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

## Run with transpect sidecars

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

The HTML flow stays unchanged. The new mode adds a separate branch:

```text
DOCX -> DOCX(native OMML)
```

Current MVP scope:

- native OMML is left untouched
- only block equations are patched first
- standalone OLE/WMF equation paragraphs are the target shape
- inline equations are intentionally deferred to a later phase
- OLE binaries are never edited directly
- if a manifest entry cannot be resolved, the original object is kept and a warning is logged

Run it with the same sidecar manifest:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  --patch-docx \
  input.docx \
  output.docx \
  --mathml-manifest work/transpect/manifest.tsv
```

Patch path architecture:

- detect `NATIVE_OMML`, `OLE_BIN`, `WMF_PREVIEW`, `UNKNOWN`
- reuse manifest exact match first, then unique leaf-name fallback
- normalize sidecar MathML
- convert MathML -> OMML through `mml2omml.xsl` + Saxon
- inject OMML back into the DOCX for block-equation paragraphs

Manual smoke path:

```bash
java -jar target/docx-html-math-1.0.0-jar-with-dependencies.jar \
  --patch-docx \
  in/Hoa_Ha_Tinh_L1.docx \
  out/Hoa_Ha_Tinh_L1-omml.docx \
  --mathml-manifest work/batches/convert-chem-no-leading-underscore-hoa-ha-tinh-l1-20260421-181615-03/Hoa_Ha_Tinh_L1/manifest.tsv
```

## CLI options

```text
java -jar ... <input.docx> <output.html> [--native-mathml-only] [--mathml-manifest manifest.tsv] [--subject ...] [--output-mode internal|publish]
java -jar ... --patch-docx <input.docx> <output.docx> [--mathml-manifest manifest.tsv]
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

This branch is designed for the real-world case:

- **OMML** -> handled directly in Java
- **MathType WMF/OLE** -> handled by transpect outside Java, then fed back as sidecars

It does **not** attempt to embed the full transpect stack into Maven.
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
