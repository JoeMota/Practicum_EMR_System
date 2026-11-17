#!/usr/bin/env bash
# NFR-19: wake a sleeping Render API and confirm /health before a client demo.
set -euo pipefail

BASE_URL="${1:-${VITE_API_URL:-http://localhost:8000}}"
BASE_URL="${BASE_URL%/}"
TRIES="${WARM_TRIES:-40}"
SLEEP_SECS="${WARM_SLEEP:-3}"

echo "Warming ${BASE_URL}/health …"
for ((i = 1; i <= TRIES; i++)); do
  if curl -fsS "${BASE_URL}/health" >/dev/null; then
    echo "API is up (attempt ${i})."
    exit 0
  fi
  echo "  waiting (${i}/${TRIES})…"
  sleep "${SLEEP_SECS}"
done

echo "API did not respond at ${BASE_URL}/health" >&2
exit 1
