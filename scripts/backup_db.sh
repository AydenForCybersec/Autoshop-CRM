#!/bin/bash
# backup_db.sh
set -euo pipefail

if [ -z "${DB_NAME:-}" ]; then
  echo "❌ DB_NAME is required."
  exit 1
fi

if [ -z "${DB_PASSWORD:-}" ]; then
  echo "❌ DB_PASSWORD is required."
  exit 1
fi

TIMESTAMP=$(date +"%Y%m%d-%H%M")
OUTDIR="${OUTDIR:-$(pwd)/backups}"
mkdir -p "$OUTDIR"
mysqldump \
  -h "${DB_HOST:-localhost}" \
  -P "${DB_PORT:-3306}" \
  -u "${DB_USER:-root}" \
  -p"${DB_PASSWORD}" \
  "${DB_NAME}" > "$OUTDIR/${DB_NAME}-$TIMESTAMP.sql"
echo "Backup saved to $OUTDIR/${DB_NAME}-$TIMESTAMP.sql"
