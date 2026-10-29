#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.prod.yml}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Нет файла настроек: $ENV_FILE" >&2
  echo "Скопируйте .env.prod.example в .env.prod и заполните." >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

usage() {
  cat <<'EOF'
Использование: scripts/prod.sh <команда>

  up        собрать образы и поднять стек (первый запуск и обновление)
  start     поднять уже собранные образы
  down      остановить стек (данные и медиа сохраняются)
  ps        статус контейнеров
  logs [s]  логи (можно указать сервис: backend, web, postgres, migrate)
  migrate   выполнить миграции вручную
  backup    сделать бэкап БД и медиа
  config    проверить compose-файл
  exec ...  выполнить команду в контейнере, например: exec backend bash

Перед запуском: cp .env.prod.example .env.prod && заполнить .env.prod
EOF
}

case "${1:-}" in
  up)
    compose up -d --build
    ;;
  start)
    compose up -d
    ;;
  down)
    compose down
    ;;
  ps)
    compose ps
    ;;
  logs)
    shift
    compose logs -f --tail=200 "$@"
    ;;
  migrate)
    compose run --rm migrate
    ;;
  backup)
    ENV_FILE="$ENV_FILE" "$ROOT/scripts/backup.sh"
    ;;
  config)
    compose config
    ;;
  exec)
    shift
    compose exec "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
