#!/bin/bash
# Dump the local MySQL container and ship the dump off this server.
#
# The whole point is the "off this server" part: a dump sitting next to the
# database it came from does not survive the disk failure you are backing up
# against. If the upload fails, this script fails loudly and keeps every local
# copy rather than pruning.
#
# Cron (daily 03:15, log to syslog):
#   15 3 * * * /path/to/wykoj/scripts/backup.sh 2>&1 | logger -t wykoj-backup
set -euo pipefail

cd "$(dirname "$0")/.."

[[ -f .env ]] || { echo "FATAL: .env not found" >&2; exit 1; }
set -a; source .env; set +a

: "${MYSQL_ROOT_PASSWORD:?not set in .env}"
: "${BACKUP_RCLONE_DEST:?not set in .env}"

DB_NAME="${MYSQL_DATABASE:-wykojdb}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
CONTAINER="wykoj-db"

BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="$BACKUP_DIR/${DB_NAME}-${STAMP}.sql.gz"

echo "[$(date -uIs)] dumping $DB_NAME -> $DUMP"

# --single-transaction: consistent snapshot without locking writers (InnoDB).
# --no-tablespaces: avoids needing the PROCESS privilege on MySQL 8.
# --default-character-set: keeps CJK content in User.name intact.
docker exec "$CONTAINER" mysqldump \
    --user=root --password="$MYSQL_ROOT_PASSWORD" \
    --single-transaction \
    --routines --triggers --events \
    --no-tablespaces \
    --default-character-set=utf8mb4 \
    "$DB_NAME" \
  | gzip -9 > "$DUMP"

# mysqldump can die midway and still leave a plausible-looking file. Verify the
# gzip stream is intact and that the dump reached its own end marker.
gzip -t "$DUMP"
if ! zcat "$DUMP" | tail -5 | grep -q "Dump completed"; then
    echo "FATAL: dump is truncated, refusing to ship or prune" >&2
    mv "$DUMP" "$DUMP.CORRUPT"
    exit 1
fi

SIZE="$(du -h "$DUMP" | cut -f1)"
echo "[$(date -uIs)] dump ok ($SIZE), uploading to $BACKUP_RCLONE_DEST"

# Remote retention is the bucket's lifecycle rule, not this script: the
# uploader deliberately lacks delete permission, so pruning happens server-side.
rclone copy "$DUMP" "$BACKUP_RCLONE_DEST"

# rclone copy exits 0 if it uploaded nothing at all, so confirm the object is
# actually there before pruning anything locally.
rclone lsf "$BACKUP_RCLONE_DEST/$(basename "$DUMP")" >/dev/null

echo "[$(date -uIs)] upload ok, pruning local dumps older than ${KEEP_DAYS}d"
find "$BACKUP_DIR" -name "${DB_NAME}-*.sql.gz" -type f -mtime "+${KEEP_DAYS}" -print -delete

echo "[$(date -uIs)] done"
