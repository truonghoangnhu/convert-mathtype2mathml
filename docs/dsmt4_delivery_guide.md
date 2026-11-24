# DSMT4 migration delivery — 2026-11-24

Release tag: `dsmt4-migration-2026.11.24`.

The delivery ZIP contains a runnable JAR, the sidecar/preparation scripts, sample fixtures, all repository documentation, the versioned acceptance snapshot, `BUILD_INFO.json` and `SHA256SUMS`. The external transpect decoder and original exam documents are not included.

The [delivery verification record](dsmt4_delivery_verification_2026-11-24.json) records the clean-directory checks, including real Hóa sidecar regeneration and a complete DOCX ZIP-part comparison against the production baseline.

## Requirements

- Java 17 or newer to run the JAR; Maven 3.9+ only when building from source.
- Python 3.9+ and Bash for the shipped scripts. The sidecar and MathML preparation scripts use the Python standard library; the repository's optional question-bank dependencies are not required for this route.
- Word for the Word output route; LibreOffice Math/Writer for the separate MathML/ODT route. Application acceptance is scoped to the recorded samples and versions, not every installed application version.

## Verify and try the archive

Extract the ZIP, open Terminal in its top-level folder, then run:

```bash
shasum -a 256 -c SHA256SUMS
mkdir -p output
java -jar lib/docx-html-math.jar \
  --patch-docx samples/sample-omml.docx output/native-omml.docx
python3 scripts/transpect/prepare_libreoffice_mathml.py \
  fixtures/dsmt4/chemistry-arrows/arrow-1.mathml \
  output/arrow-libreoffice.mathml > output/arrow-libreoffice.report.json
```

The native-OMML example preserves existing equations; it does not exercise binary MathType decoding. A prepared MathML candidate remains `needs_review` until its content, editing and placement are checked in the target application. Choose a new output path when running preparation again; the command never overwrites a file.

## Install the external decoder at the recorded revision

Run from the extracted delivery folder:

```bash
git clone https://github.com/transpect/calabash-frontend.git tools/calabash
git -C tools/calabash checkout a4cf3ae17cf117100447744e285b92fce9e3699d
git -C tools/calabash submodule update --init --recursive
```

The complete recorded dependency graph and JAR SHA-256 values are in `docs/acceptance/dsmt4-2026-11-24/provenance.json`. Compare the checkout/submodules and the two JAR hashes with that file before using a replacement runtime. Maven's Saxon 12.9 belongs to the converter; the separate transpect runtime uses its recorded Saxon-HE 10.8 JAR.

## Convert a MathType DOCX for Word

Use a fresh sidecar directory and retain the original input:

```bash
export MT_DIR="$PWD/tools/calabash/extensions/transpect/mathtype-extension"
export XMLCALABASH_JAR="$PWD/tools/calabash/distro/xmlcalabash-1.4.1-100.jar"
export SAXON_HE_JAR="$PWD/tools/calabash/distro/lib/Saxon-HE-10.8.jar"
bash scripts/transpect/generate_sidecars.sh \
  /absolute/path/input.docx "$PWD/output/sidecars" \
  "$MT_DIR" "$XMLCALABASH_JAR" "$SAXON_HE_JAR"
java -jar lib/docx-html-math.jar \
  --patch-docx /absolute/path/input.docx output/word-omml.docx \
  --mathml-manifest output/sidecars/manifest.tsv --patch-log-level summary
```

Read the patch summary and skip breakdown. Missing/unusable sidecars and unsafe placements keep the original OLE; counts are not semantic acceptance. Open the result in Word and compare it with the source.

## Use the separate LibreOffice Math route

For a chosen sidecar, run `prepare_libreoffice_mathml.py` as above, import the prepared file into LibreOffice Math, and verify edit/save/reopen and placement if embedding it in Writer. Keep the original normalized sidecars for Word. The adapter's output must not replace Word's sidecar manifest. A successful ODT check does not establish Writer DOCX import/export parity. This archive does not automatically rebuild whole Writer exam documents.

## Acceptance and limitations

[The versioned snapshot](acceptance/dsmt4-2026-11-24/README.md) records 238 accepted and 27 needs_review: 18 retained OLE and 9 presentation limitations. Outside the five-exam subset, converted equations remain needs_review; `FULL_END_ONLY` remains unsupported. Pagination/font differences allowed by the support policy, B10 row-spacing changes and height phantoms are not additional work for this release.

## Rebuild the delivery ZIP from source

From a clean checkout of the release tag:

```bash
mvn -q package
python3 -m unittest discover -s tests
python3 -m unittest discover -s scripts/workflow -p 'test_*.py'
python3 scripts/workflow/run_modern_docx_omml_generated_output_gate.py
python3 scripts/workflow/run_modern_docx_omml_smoke.py
python3 scripts/release/build_dsmt4_bundle.py
```

The bundle builder records the Git revision, rejects tracked working-tree edits and existing output files, and writes the ZIP, standalone JAR and external checksum file under `out/releases/`. Rebuilt JAR hashes can differ because Maven archives include build metadata; use the published checksums to verify downloaded release assets.
