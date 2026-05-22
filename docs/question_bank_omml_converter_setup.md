# question_bank OMML Converter Setup

Build this project before enabling the converter:

```sh
cd /absolute/path/to/transpect-branch-project
mvn -q -DskipTests package
```

Install `pandoc` and make sure it is on `PATH`. If it is installed elsewhere, set
`PANDOC_CMD` to the absolute executable path before running `question_bank`.

Configure `question_bank/backend/.env`:

```env
DOCX_MATH_CONVERTER_CMD=/absolute/path/to/transpect-branch-project/scripts/question_bank_latex_to_omml.sh
DOCX_MATH_CONVERTER_TIMEOUT_SECONDS=5
```

Converter contract for phase 1:

- stdin: raw LaTeX
- env: `DOCX_MATH_DISPLAY=1` for display math, `0` for inline math
- stdout: OMML XML only
- root: `m:oMath` for inline or `m:oMathPara` for display
- failure: non-zero exit; diagnostics may be written to stderr

Smoke check:

```sh
cd /absolute/path/to/transpect-branch-project
scripts/smoke_question_bank_omml_converter.sh
```
