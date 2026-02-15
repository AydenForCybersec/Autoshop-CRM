#!/bin/bash
# backup_db.sh
TIMESTAMP=$(date +"%Y%m%d-%H%M")
OUTDIR="/root/Autoshop-CRM/backups"
mkdir -p "$OUTDIR"
mysqldump -h ${DB_HOST:-localhost} -P ${DB_PORT:-3306} -u ${DB_USER:-root} -p"${DB_PASSWORD}" ${DB_NAME} > "$OUTDIR/${DB_NAME}-$TIMESTAMP.sql"
echo "Backup saved to $OUTDIR/${DB_NAME}-$TIMESTAMP.sql"
