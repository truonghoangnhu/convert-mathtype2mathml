#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR_PATH="${ROOT_DIR}/target/docx-html-math-1.0.0-jar-with-dependencies.jar"
PANDOC_BIN="${PANDOC_CMD:-pandoc}"
PANDOC_PROBE="${PANDOC_BIN%% *}"

if [[ ! -f "${JAR_PATH}" ]]; then
  echo "Missing ${JAR_PATH}. Run: cd ${ROOT_DIR} && mvn -q -DskipTests package" >&2
  exit 1
fi

if ! command -v java >/dev/null 2>&1; then
  echo "Missing java on PATH; install a JRE/JDK before running the LaTeX to OMML converter." >&2
  exit 127
fi

if ! command -v "${PANDOC_PROBE}" >/dev/null 2>&1; then
  echo "Missing pandoc on PATH; install pandoc or set PANDOC_CMD to its absolute path." >&2
  exit 127
fi

# Keep stdout reserved for OMML XML only. All diagnostics above and from the Java
# converter are written to stderr so question_bank can safely parse stdout.
exec java -cp "${JAR_PATH}" com.example.docxmath.LatexToOmmlCli
