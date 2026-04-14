#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)

JAR_PATH="${REVIEW_SERVER_JAR:-$REPO_ROOT/target/docx-html-math-1.0.0-jar-with-dependencies.jar}"
REVIEW_ROOT="${1:-}"
HOST="${REVIEW_SERVER_HOST:-127.0.0.1}"
PORT="${REVIEW_SERVER_PORT:-8080}"
QB_DB_URL_VALUE="${QB_DB_URL:-${DATABASE_URL:-}}"
OPERATOR_PYTHON="${QB_OPERATOR_PYTHON:-${QUESTION_BANK_PYTHON:-${PYTHON:-python3}}}"

if [ -z "$REVIEW_ROOT" ]; then
  echo "Usage: $0 <review-root> [host] [port]" >&2
  exit 2
fi

if [ ! -f "$JAR_PATH" ]; then
  echo "[ERROR] Review server jar not found: $JAR_PATH" >&2
  echo "[ERROR] Build first with: mvn -q -DskipTests package" >&2
  exit 2
fi

if [ ! -d "$REVIEW_ROOT" ]; then
  echo "[ERROR] Review root not found: $REVIEW_ROOT" >&2
  exit 2
fi

if [ "$#" -ge 2 ]; then
  HOST="$2"
fi
if [ "$#" -ge 3 ]; then
  PORT="$3"
fi

JAVA_ARGS=(
  -cp "$JAR_PATH"
  com.example.docxmath.ReviewServerCli
  --review-root "$REVIEW_ROOT"
  --host "$HOST"
  --port "$PORT"
  --python-executable "$OPERATOR_PYTHON"
)

if [ -n "$QB_DB_URL_VALUE" ]; then
  JAVA_ARGS+=(--question-bank-db-url "$QB_DB_URL_VALUE")
fi

exec java "${JAVA_ARGS[@]}"
