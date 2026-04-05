#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 7 ]; then
  echo "Usage: $0 <input.docx> <output.html> <project-jar> <mathtype-extension-dir> <xmlcalabash-jar> <saxon-he-jar> <work-dir> [transpect-config.xml] [converter-args...]" >&2
  exit 1
fi

INPUT_DOCX="$1"
OUTPUT_HTML="$2"
PROJECT_JAR="$3"
MATHTYPE_DIR="$4"
XMLCALABASH_JAR="$5"
SAXON_JAR="$6"
WORK_DIR="$7"
shift 7

TRANSPECT_CONFIG=""
if [ "$#" -gt 0 ] && [[ "$1" != --* ]]; then
  TRANSPECT_CONFIG="$1"
  shift
fi

JAVA_ARGS=("$@")

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
mkdir -p "$WORK_DIR"

validate_explicit_input() {
  local input_lower
  input_lower=$(printf '%s' "$INPUT_DOCX" | tr '[:upper:]' '[:lower:]')
  case "$input_lower" in
    *.docx) ;;
    *)
      echo "[ERROR] Explicit input must be a .docx source file. Got: $INPUT_DOCX" >&2
      exit 2
      ;;
  esac
  if [ ! -f "$INPUT_DOCX" ]; then
    echo "[ERROR] Input DOCX not found: $INPUT_DOCX" >&2
    exit 2
  fi
  case "$input_lower" in
    *-transpect.html|*.qa.json|*.qa.md|*.before_after.diff.md|*"_files/"*|*"/_files/"*)
      echo "[ERROR] Refusing non-source input artifact: $INPUT_DOCX" >&2
      exit 2
      ;;
  esac
}

canon_path() {
  python3 - <<'PY' "$1"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
}

sha256_file() {
  python3 - <<'PY' "$1"
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
digest = hashlib.sha256()
with path.open("rb") as fh:
    while True:
        chunk = fh.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
print(digest.hexdigest())
PY
}

validate_explicit_input

CANONICAL_INPUT_DOCX="$(canon_path "$INPUT_DOCX")"
LOCK_ROOT="${DOCX_INPUT_LOCK_ROOT:-$REPO_ROOT/work/.input-locks}"
mkdir -p "$LOCK_ROOT"
INPUT_LOCK_KEY="$(python3 - <<'PY' "$CANONICAL_INPUT_DOCX"
import hashlib
import sys
print(hashlib.sha256(sys.argv[1].encode("utf-8")).hexdigest())
PY
)"
INPUT_LOCK_DIR="$LOCK_ROOT/$INPUT_LOCK_KEY.lock"
LOCK_STALE_SECONDS="${DOCX_LOCK_STALE_SECONDS:-21600}"
RUN_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
acquire_lock() {
  mkdir "$INPUT_LOCK_DIR" 2>/dev/null
}
if ! acquire_lock; then
  existing_pid=""
  existing_timestamp=""
  if [ -f "$INPUT_LOCK_DIR/pid" ]; then
    existing_pid="$(tr -dc '0-9' < "$INPUT_LOCK_DIR/pid" || true)"
  fi
  if [ -f "$INPUT_LOCK_DIR/timestamp" ]; then
    existing_timestamp="$(tr -dc '0-9' < "$INPUT_LOCK_DIR/timestamp" || true)"
  fi
  now_ts="$(python3 - <<'PY'
import time
print(int(time.time()))
PY
)"
  lock_age=-1
  if [ -n "$existing_timestamp" ]; then
    lock_age=$(( now_ts - existing_timestamp ))
    if [ "$lock_age" -lt 0 ]; then
      lock_age=-1
    fi
  fi
  pid_alive=0
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    pid_alive=1
  fi
  is_stale=0
  if [ "$pid_alive" -eq 0 ]; then
    is_stale=1
  elif [ "$lock_age" -ge 0 ] && [ "$lock_age" -gt "$LOCK_STALE_SECONDS" ]; then
    is_stale=1
  fi
  if [ "$is_stale" -eq 1 ]; then
    echo "[WARN] Recovering stale lock for input: $CANONICAL_INPUT_DOCX (run_id=$RUN_ID, pid=${existing_pid:-unknown}, age_sec=${lock_age})"
    rm -rf "$INPUT_LOCK_DIR" >/dev/null 2>&1 || true
    if ! acquire_lock; then
      echo "[ERROR] Failed to recover stale lock for input: $CANONICAL_INPUT_DOCX" >&2
      exit 3
    fi
  else
    echo "[ERROR] Conversion already in progress for input: $CANONICAL_INPUT_DOCX (run_id=$RUN_ID, pid=${existing_pid:-unknown}, age_sec=${lock_age})" >&2
    exit 3
  fi
fi
cleanup_lock() {
  rm -rf "$INPUT_LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup_lock EXIT
printf '%s\n' "$CANONICAL_INPUT_DOCX" > "$INPUT_LOCK_DIR/input.path"
printf '%s\n' "$$" > "$INPUT_LOCK_DIR/pid"
printf '%s\n' "$(python3 - <<'PY'
import time
print(int(time.time()))
PY
)" > "$INPUT_LOCK_DIR/timestamp"
printf '%s\n' "$RUN_ID" > "$INPUT_LOCK_DIR/run_id"

now_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

ms_to_sec() {
  python3 - <<'PY' "$1" "$2"
import sys
start = int(sys.argv[1])
end = int(sys.argv[2])
print(f"{(end - start) / 1000.0:.3f}")
PY
}

compute_cache_key() {
  python3 - <<'PY' \
    "$INPUT_DOCX" "$OUTPUT_HTML" "$PROJECT_JAR" "$MATHTYPE_DIR" "$XMLCALABASH_JAR" "$SAXON_JAR" "$TRANSPECT_CONFIG" \
    "$SCRIPT_DIR/run_docx_with_transpect.sh" "$SCRIPT_DIR/generate_sidecars.sh" \
    "${JAVA_ARGS[@]}"
import json
import os
import sys
import hashlib
from pathlib import Path

input_docx = Path(sys.argv[1]).resolve()
output_html = Path(sys.argv[2]).resolve()
project_jar = Path(sys.argv[3]).resolve()
mathtype_dir = Path(sys.argv[4]).resolve()
xmlcalabash_jar = Path(sys.argv[5]).resolve()
saxon_jar = Path(sys.argv[6]).resolve()
transpect_config = Path(sys.argv[7]).resolve() if sys.argv[7] else None
run_script = Path(sys.argv[8]).resolve()
sidecar_script = Path(sys.argv[9]).resolve()
java_args = sys.argv[10:]

def fp(path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        st = path.stat()
        return f"{st.st_size}:{st.st_mtime_ns}"
    except FileNotFoundError:
        return "missing"

def sha256(path: Path | None) -> str:
    if path is None:
        return "none"
    try:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except FileNotFoundError:
        return "missing"

def dir_fp(path: Path) -> str:
    # Cheap but stable-enough fingerprint for bundled tool dirs.
    try:
        st = path.stat()
        return f"{st.st_mtime_ns}:{st.st_size}"
    except FileNotFoundError:
        return "missing"

payload = {
    "input_docx": str(input_docx),
    "input_sha256": sha256(input_docx),
    "output_html": str(output_html),
    "project_jar": str(project_jar),
    "project_jar_fp": fp(project_jar),
    "mathtype_dir": str(mathtype_dir),
    "mathtype_dir_fp": dir_fp(mathtype_dir),
    "xmlcalabash_jar": str(xmlcalabash_jar),
    "xmlcalabash_jar_fp": fp(xmlcalabash_jar),
    "saxon_jar": str(saxon_jar),
    "saxon_jar_fp": fp(saxon_jar),
    "transpect_config": str(transpect_config) if transpect_config else "",
    "transpect_config_fp": fp(transpect_config) if transpect_config else "none",
    "run_script_fp": fp(run_script),
    "sidecar_script_fp": fp(sidecar_script),
    "java_args": java_args,
    "docx_force_rebuild_env": os.environ.get("DOCX_FORCE_REBUILD", ""),
}
raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
print(hashlib.sha256(raw).hexdigest())
PY
}

CACHE_KEY_FILE="$WORK_DIR/.publish-run-cache.key"
RUN_TIMINGS_FILE="$WORK_DIR/run.timings.tsv"
FORCE_REBUILD="${DOCX_FORCE_REBUILD:-0}"
CACHE_KEY="$(compute_cache_key)"
OUTPUT_CANONICAL="$(canon_path "$OUTPUT_HTML")"
OUTPUT_DIR_CANONICAL="$(canon_path "$(dirname "$OUTPUT_HTML")")"
INPUT_SHA256="$(sha256_file "$INPUT_DOCX")"

START_REASON="forced rebuild (DOCX_FORCE_REBUILD=1)"
if [ "$FORCE_REBUILD" != "1" ]; then
  if [ ! -f "$CACHE_KEY_FILE" ]; then
    START_REASON="no cache key present"
  elif [ ! -f "$OUTPUT_HTML" ]; then
    START_REASON="output HTML missing"
  elif [ ! -f "$WORK_DIR/manifest.tsv" ]; then
    START_REASON="MathML manifest missing"
  elif [ "$(cat "$CACHE_KEY_FILE")" != "$CACHE_KEY" ]; then
    START_REASON="input/toolchain hash changed"
  else
    START_REASON=""
  fi
fi

if [ -z "$START_REASON" ]; then
  echo "[INFO] Conversion cache hit: unchanged input hash/toolchain; reusing existing output."
  echo "[INFO] Run ID: $RUN_ID"
  echo "[INFO] Input: $CANONICAL_INPUT_DOCX"
  echo "[INFO] Output: $OUTPUT_CANONICAL"
  echo "[INFO] Output directory (excluded from discovery policy): $OUTPUT_DIR_CANONICAL"
  echo "[INFO] Input SHA-256: $INPUT_SHA256"
  if [ -f "$RUN_TIMINGS_FILE" ]; then
    echo "Run timings written to: $RUN_TIMINGS_FILE"
    cat "$RUN_TIMINGS_FILE"
  fi
  exit 0
fi

echo "[INFO] Conversion start reason: $START_REASON"
echo "[INFO] Run ID: $RUN_ID"
echo "[INFO] Input: $CANONICAL_INPUT_DOCX"
echo "[INFO] Output: $OUTPUT_CANONICAL"
echo "[INFO] Output directory (excluded from discovery policy): $OUTPUT_DIR_CANONICAL"
echo "[INFO] Input SHA-256: $INPUT_SHA256"

t_total_start=$(now_ms)
t_sidecar_start=$(now_ms)
if [ -n "$TRANSPECT_CONFIG" ]; then
  "$SCRIPT_DIR/generate_sidecars.sh" "$INPUT_DOCX" "$WORK_DIR" "$MATHTYPE_DIR" "$XMLCALABASH_JAR" "$SAXON_JAR" "$TRANSPECT_CONFIG"
else
  "$SCRIPT_DIR/generate_sidecars.sh" "$INPUT_DOCX" "$WORK_DIR" "$MATHTYPE_DIR" "$XMLCALABASH_JAR" "$SAXON_JAR"
fi
t_sidecar_end=$(now_ms)

t_converter_start=$(now_ms)
java -Djava.awt.headless=true -jar "$PROJECT_JAR" "$INPUT_DOCX" "$OUTPUT_HTML" --mathml-manifest "$WORK_DIR/manifest.tsv" "${JAVA_ARGS[@]}"
t_converter_end=$(now_ms)
t_total_end=$(now_ms)

sidecar_sec=$(ms_to_sec "$t_sidecar_start" "$t_sidecar_end")
converter_sec=$(ms_to_sec "$t_converter_start" "$t_converter_end")
total_sec=$(ms_to_sec "$t_total_start" "$t_total_end")

printf "phase\tseconds\n" > "$RUN_TIMINGS_FILE"
printf "sidecar-generation\t%s\n" "$sidecar_sec" >> "$RUN_TIMINGS_FILE"
printf "java-conversion\t%s\n" "$converter_sec" >> "$RUN_TIMINGS_FILE"
printf "total\t%s\n" "$total_sec" >> "$RUN_TIMINGS_FILE"

printf '%s' "$CACHE_KEY" > "$CACHE_KEY_FILE"

echo "Run timings written to: $RUN_TIMINGS_FILE"
cat "$RUN_TIMINGS_FILE"
