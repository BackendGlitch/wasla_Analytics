#!/bin/sh
set -e

# Artifacts arrive via the read-only /repo mount (see docker-compose.yml).
# If they're absent the API still boots in degraded mode — /api/health explains.
if [ -d "${ARTIFACTS_DIR:-/repo}" ]; then
  echo "artifacts: ${ARTIFACTS_DIR:-/repo}"
else
  echo "WARN: ARTIFACTS_DIR not found — API will start degraded"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
