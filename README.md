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

## Why this branch exists

For documents that contain many legacy MathType equations, a POI-only converter usually falls back to preview images.
This branch adds a second stage:

- first generate **MathML sidecars** from `/word/media/*.wmf` and `/word/embeddings/*.bin`
- then let the Java converter replace matching DOCX assets with real MathML

That keeps the final HTML semantic and web-friendly.

## Repository layout

- `src/main/java/...` Java converter
- `src/main/resources/omml2mml.xsl` open-source OMML -> MathML stylesheet
- `scripts/transpect/generate_sidecars.sh` run transpect on extracted WMF/BIN files
- `scripts/transpect/run_docx_with_transpect.sh` end-to-end wrapper

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

## CLI options

```text
java -jar ... <input.docx> <output.html> [--native-mathml-only] [--mathml-manifest manifest.tsv]
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
See `THIRD_PARTY_LICENSES_transpect_docx2hub_BSD-2-Clause.txt`.
