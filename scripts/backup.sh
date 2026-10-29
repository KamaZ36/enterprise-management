#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Нет файла настроек: $ENV_FILE" >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

running="$(compose ps --status running --services 2>/dev/null || true)"
for service in postgres backend; do
  if ! grep -qx "$service" <<<"$running"; then
    echo "Сервис $service не запущен — сначала выполните scripts/prod.sh up" >&2
    exit 1
  fi
done

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB_FILE="$BACKUP_DIR/db-$STAMP.sql.gz"
MEDIA_FILE="$BACKUP_DIR/media-$STAMP.tgz"

echo "Дамп базы..."
if ! compose exec -T postgres sh -c \
  'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --clean --if-exists' \
  | gzip >"$DB_FILE"; then
  echo "Дамп базы не удался" >&2
  rm -f "$DB_FILE" "$MEDIA_FILE"
  exit 1
fi

echo "Архив медиа..."
if ! compose exec -T backend tar -czf - -C /app media >"$MEDIA_FILE"; then
  echo "Архив медиа не удался" >&2
  rm -f "$DB_FILE" "$MEDIA_FILE"
  exit 1
fi

for file in "$DB_FILE" "$MEDIA_FILE"; do
  if [[ ! -s "$file" ]]; then
    echo "Бэкап не удался: пустой файл $file" >&2
    rm -f "$DB_FILE" "$MEDIA_FILE"
    exit 1
  fi
done

prune() {
  local pattern="$1"
  mapfile -t old < <(
    ls -1t "$BACKUP_DIR"/$pattern 2>/dev/null \
      | tail -n "+$((BACKUP_KEEP + 1))" || true
  )
  if (( ${#old[@]} > 0 )); then
    rm -f "${old[@]}"
  fi
}
prune 'db-*.sql.gz'
prune 'media-*.tgz'

printf 'Бэкап готов:\n  %s (%s)\n  %s (%s)\n' \
  "$DB_FILE" "$(du -h "$DB_FILE" | cut -f1)" \
  "$MEDIA_FILE" "$(du -h "$MEDIA_FILE" | cut -f1)"
