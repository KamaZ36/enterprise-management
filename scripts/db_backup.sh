#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
CONTAINER="${MD_POSTGRES_CONTAINER:-md-postgres}"

env_value() {
  local key="$1" default="$2" value
  value="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ROOT/.env" 2>/dev/null \
    | tail -1 | cut -d= -f2- \
    | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
          -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"
  printf '%s' "${value:-$default}"
}

DB_USER="${DB_USER:-$(env_value DB_USER user)}"
DB_PASSWORD="${DB_PASSWORD:-$(env_value DB_PASSWORD password)}"
DB_DATABASE="${DB_DATABASE:-$(env_value DB_DATABASE database)}"
DB_PORT="${DB_PORT:-$(env_value DB_PORT 5432)}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/${DB_DATABASE}-${STAMP}.sql.gz"

dump() {
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
    docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER" \
      pg_dump --username "$DB_USER" --dbname "$DB_DATABASE" \
      --clean --if-exists
  else
    PGPASSWORD="$DB_PASSWORD" pg_dump \
      --host "$(env_value DB_HOST localhost)" --port "$DB_PORT" \
      --username "$DB_USER" --dbname "$DB_DATABASE" \
      --clean --if-exists
  fi
}

if ! dump | gzip > "$FILE"; then
  rm -f "$FILE"
  echo "Бэкап не удался: pg_dump вернул ошибку" >&2
  exit 1
fi

if [[ ! -s "$FILE" ]]; then
  rm -f "$FILE"
  echo "Бэкап не удался: пустой файл" >&2
  exit 1
fi

mapfile -t old < <(ls -1t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -n "+$((BACKUP_KEEP + 1))" || true)
if (( ${#old[@]} > 0 )); then
  rm -f "${old[@]}"
fi

printf 'Бэкап готов: %s (%s, хранится %s)\n' \
  "$FILE" "$(du -h "$FILE" | cut -f1)" "$BACKUP_KEEP"
