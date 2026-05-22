#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${ROOT_DIR}/scripts/question_bank_latex_to_omml.sh"
QB_BACKEND_DIR="${QB_BACKEND_DIR:-${ROOT_DIR}/../question_bank/backend}"

inline_out="$(mktemp)"
display_out="$(mktemp)"
bad_out="$(mktemp)"
bad_err="$(mktemp)"
cleanup() {
  rm -f "${inline_out}" "${display_out}" "${bad_out}" "${bad_err}"
}
trap cleanup EXIT

printf 'x^2+1' | DOCX_MATH_DISPLAY=0 "${WRAPPER}" >"${inline_out}"
python3 - "${inline_out}" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
expected = "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath"
if root.tag != expected:
    raise SystemExit(f"expected inline root {expected}, got {root.tag}")
PY

printf '\\frac{a}{b}' | DOCX_MATH_DISPLAY=1 "${WRAPPER}" >"${display_out}"
python3 - "${display_out}" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
expected = "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara"
if root.tag != expected:
    raise SystemExit(f"expected display root {expected}, got {root.tag}")
PY

if printf '\\notarealcommand{' | DOCX_MATH_DISPLAY=0 "${WRAPPER}" >"${bad_out}" 2>"${bad_err}"; then
  echo "Expected bad LaTeX conversion to fail, but it exited zero." >&2
  exit 1
fi

if [[ ! -d "${QB_BACKEND_DIR}" ]]; then
  echo "Missing question_bank backend at ${QB_BACKEND_DIR}; set QB_BACKEND_DIR to run Django smoke tests." >&2
  exit 1
fi

(
  cd "${QB_BACKEND_DIR}"
  PYTHON_BIN="python"
  if [[ -x "venv/bin/python" ]]; then
    PYTHON_BIN="venv/bin/python"
  fi
  "${PYTHON_BIN}" manage.py test importer.tests_exam_generation.DocxMathRenderTests --keepdb
)

echo "question_bank OMML converter smoke passed"
