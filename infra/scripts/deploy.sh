#!/usr/bin/env bash
# Simple deploy script to run on the VPS from /opt/aura.
# Pulls the latest images, brings the stack up, runs migrations via the api entrypoint.
set -euo pipefail

cd "$(dirname "$0")/../compose"

echo "==> Pulling images"
docker compose -f docker-compose.prod.yml pull

echo "==> Bringing stack up"
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "==> Healthcheck"
for i in {1..30}; do
  if curl -fsS http://localhost/health >/dev/null 2>&1 || \
     curl -fsS https://api.${AURA_DOMAIN:-aura.local}/health >/dev/null 2>&1; then
    echo "OK"
    exit 0
  fi
  sleep 2
done

echo "Healthcheck failed" >&2
exit 1
