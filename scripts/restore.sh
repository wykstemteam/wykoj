#!/bin/bash
# Restore a dump produced by backup.sh into the local MySQL container.
#
#   ./scripts/restore.sh backups/wykojdb-20260808T031500Z.sql.gz
#
# DESTRUCTIVE: overwrites the current contents of the database. Rehearse this
# at least once against a throwaway database - a backup you have never restored
# is a backup you do not know you have.
set -euo pipefail

cd "$(dirname "$0")/.."

DUMP="${1:-}"
[[ -f "$DUMP" ]] || { echo "usage: $0 <dump.sql.gz>" >&2; exit 1; }

[[ -f .env ]] || { echo "FATAL: .env not found" >&2; exit 1; }
set -a; source .env; set +a
: "${MYSQL_ROOT_PASSWORD:?not set in .env}"
DB_NAME="${MYSQL_DATABASE:-wykojdb}"
CONTAINER="wykoj-db"

gzip -t "$DUMP"

echo "About to overwrite database '$DB_NAME' in container '$CONTAINER'"
echo "with: $DUMP"
read -rp "Type the database name to confirm: " CONFIRM
[[ "$CONFIRM" == "$DB_NAME" ]] || { echo "aborted" >&2; exit 1; }

echo "restoring..."
zcat "$DUMP" | docker exec -i "$CONTAINER" mysql \
    --user=root --password="$MYSQL_ROOT_PASSWORD" \
    --default-character-set=utf8mb4 \
    "$DB_NAME"

echo "restored. Spot-check before trusting it:"
docker exec "$CONTAINER" mysql --user=root --password="$MYSQL_ROOT_PASSWORD" \
    --default-character-set=utf8mb4 -e \
    "SELECT 'user',COUNT(*) FROM user UNION ALL
     SELECT 'task',COUNT(*) FROM task UNION ALL
     SELECT 'submission',COUNT(*) FROM submission;" "$DB_NAME"
