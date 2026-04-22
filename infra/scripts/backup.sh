#!/usr/bin/env bash
# Daily Postgres backup to R2, encrypted with age.
# Scheduled via cron (03:00 UTC). See docs/devops/deployment.md.
set -euo pipefail

: "${R2_BUCKET_BACKUPS:?R2_BUCKET_BACKUPS is required}"
: "${AGE_RECIPIENT:?AGE_RECIPIENT is required}"

DATE=$(date -u +"%Y/%m/%d")
FILE="/tmp/perdiz_${DATE//\//_}.dump"

echo "==> pg_dump"
docker exec perdiz-prod-postgres-1 pg_dump -Fc -U perdiz perdiz > "${FILE}"

echo "==> encrypt"
age -r "${AGE_RECIPIENT}" -o "${FILE}.age" "${FILE}"
rm "${FILE}"

echo "==> upload to R2"
aws --endpoint-url "${R2_ENDPOINT_URL}" s3 cp "${FILE}.age" \
  "s3://${R2_BUCKET_BACKUPS}/postgres/${DATE}.dump.age"

rm "${FILE}.age"
echo "OK"
