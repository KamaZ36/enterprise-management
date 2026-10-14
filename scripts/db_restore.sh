#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FILE="${1:-}"
if [[ -z "$FILE" || ! -f "$FILE" ]]; then
  echo "Использование: $0 <файл.sql.gz>" >&2
  exit 1
fi

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

if [[ "${FORCE:-}" != "1" ]]; then
  read -r -p "Перезаписать базу '$DB_DATABASE' из '$FILE'? [y/N] " answer
  [[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "Отменено"; exit 0; }
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  gunzip -c "$FILE" | docker exec -i -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER" \
    psql --username "$DB_USER" --dbname "$DB_DATABASE" -v ON_ERROR_STOP=1
else
  gunzip -c "$FILE" | PGPASSWORD="$DB_PASSWORD" psql \
    --host "$(env_value DB_HOST localhost)" --port "$DB_PORT" \
    --username "$DB_USER" --dbname "$DB_DATABASE" -v ON_ERROR_STOP=1
fi

echo "База '$DB_DATABASE' восстановлена из '$FILE'"
