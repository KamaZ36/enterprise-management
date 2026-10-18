#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_DIR="$ROOT/.tmp/dev"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

BACKEND_PORT=8000
ADMIN_PORT=3000
LANDING_PORT=3001
CAFE_PORT=3002

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
ok()  { printf '   ✓ %s\n' "$1"; }
bad() { printf '   ✗ %s\n' "$1"; }

frontend_env() {
  export PNPM_HOME="$ROOT/frontend/.pnpm-home"
  export XDG_DATA_HOME="$PNPM_HOME/data"
  export XDG_CACHE_HOME="$PNPM_HOME/cache"
  export XDG_CONFIG_HOME="$PNPM_HOME/config"
}

port_open() { ss -tln 2>/dev/null | grep -q ":$1 "; }

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    return 1
  fi
}

db_up() {
  # Базе всё равно, кто её поднял: compose, systemd или руками.
  if port_open 5432; then
    ok "Postgres уже слушает порт 5432"
    return 0
  fi

  local compose
  if ! compose="$(compose_cmd)"; then
    bad "порт 5432 закрыт, и нет ни «docker compose», ни «docker-compose»"
    printf '      Arch:   sudo pacman -S docker-compose\n'
    printf '      Debian: sudo apt install docker-compose-v2\n'
    return 1
  fi

  # shellcheck disable=SC2086
  $compose up -d postgres >/dev/null 2>&1 || {
    bad "не удалось поднять Postgres через «$compose»"
    return 1
  }
  ok "Postgres запущен через «$compose»"
}

wait_port() {
  local port="$1" name="$2" tries="${3:-60}"
  for ((i = 0; i < tries; i++)); do
    if port_open "$port"; then ok "$name на порту $port"; return 0; fi
    sleep 1
  done
  bad "$name не поднялся на порту $port — смотрите $LOG_DIR"
  return 1
}

wait_http() {
  local port="$1" name="$2" path="${3:-/}" tries="${4:-120}"
  for ((i = 0; i < tries; i++)); do
    local code
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:$port$path" || true)"
    if [[ "$code" =~ ^(200|30[0-9]|401|403)$ ]]; then ok "$name отвечает"; return 0; fi
    sleep 1
  done
  bad "$name не отвечает на порту $port — смотрите $LOG_DIR"
  return 1
}

read_pid() {
  local name="$1" file="$RUN_DIR/$name.pid"
  [[ -f "$file" ]] || return 1
  local pid; pid="$(cat "$file")"
  kill -0 "$pid" 2>/dev/null || return 1
  echo "$pid"
}

start() {
  local name="$1"; shift
  local pid
  if pid="$(read_pid "$name")"; then ok "$name уже запущен (pid $pid)"; return 0; fi
  nohup "$@" >"$LOG_DIR/$name.log" 2>&1 &
  echo $! >"$RUN_DIR/$name.pid"
  ok "$name запущен (pid $!)"
}

cmd_up() {
  say "Проверка окружения"
  if [[ ! -f "$ROOT/.env" ]]; then
    bad "нет файла .env — скопируйте .env.example в .env"
    printf '      и заполните LOGIN_CODE_SECRET (без него приложение не стартует)\n'
    return 1
  fi
  if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    bad "нет виртуального окружения — выполните: uv sync --all-groups"
    return 1
  fi
  ok "окружение на месте"

  say "База данных"
  db_up || return 1
  wait_port 5432 "Postgres" 60 || return 1

  say "Миграции"
  TMPDIR="$ROOT/.tmp" DB_HOST=localhost .venv/bin/alembic upgrade head 2>&1 | tail -1
  ok "схема обновлена"

  say "Сервисы"
  start backend env TMPDIR="$ROOT/.tmp" DB_HOST=localhost \
    .venv/bin/uvicorn --factory myasnaya_derevnya.main:create_app \
    --no-access-log \
    --host 127.0.0.1 --port "$BACKEND_PORT"
  wait_http "$BACKEND_PORT" "Бэкенд" /docs 90 || return 1

  frontend_env
  start admin pnpm --dir frontend/apps/admin dev
  start landing pnpm --dir frontend/apps/landing dev
  start cafe pnpm --dir frontend/apps/cafe dev

  wait_http "$ADMIN_PORT" "Админка" / 150 || true
  wait_http "$LANDING_PORT" "Лендинг" / 150 || true
  wait_http "$CAFE_PORT" "Кафе" / 150 || true

  say "Готово"
  printf '   Админка:  http://127.0.0.1:%s   (вход admin / admin)\n' "$ADMIN_PORT"
  printf '   Кафе:     http://127.0.0.1:%s\n' "$CAFE_PORT"
  printf '   Лендинг:  http://127.0.0.1:%s\n' "$LANDING_PORT"
  printf '   API:      http://127.0.0.1:%s/docs\n' "$BACKEND_PORT"
  printf '\n   Логи:     %s\n' "$LOG_DIR"
  printf '   Остановка: scripts/dev.sh down\n'
}

cmd_down() {
  say "Остановка сервисов"
  for name in landing cafe admin backend; do
    if pid="$(read_pid "$name")"; then
      kill "$pid" 2>/dev/null || true
      rm -f "$RUN_DIR/$name.pid"
      ok "$name остановлен"
    else
      rm -f "$RUN_DIR/$name.pid"
      printf '   · %s не запущен\n' "$name"
    fi
  done
  if [[ "${1:-}" == "--all" ]]; then
    if compose="$(compose_cmd)"; then
      # shellcheck disable=SC2086
      $compose stop postgres >/dev/null 2>&1 || true
    fi
    ok "Postgres остановлен"
  else
    printf '   · Postgres оставлен работать (остановить: scripts/dev.sh down --all)\n'
  fi
}

cmd_status() {
  say "Состояние"
  for pair in "backend:$BACKEND_PORT" "admin:$ADMIN_PORT" "landing:$LANDING_PORT" "cafe:$CAFE_PORT"; do
    name="${pair%%:*}"; port="${pair##*:}"
    if pid="$(read_pid "$name")"; then
      printf '   %-8s pid %-7s порт %s\n' "$name" "$pid" "$(port_open "$port" && echo открыт || echo закрыт)"
    else
      printf '   %-8s не запущен\n' "$name"
    fi
  done
  printf '   %-8s %s\n' "postgres" "$(docker ps --filter name=md-postgres --format '{{.Status}}' | head -1)"
}

cmd_logs() {
  local name="${1:-backend}"
  tail -n 40 -f "$LOG_DIR/$name.log"
}

cmd_backup() {
  "$ROOT/scripts/db_backup.sh"
}

case "${1:-up}" in
  up)     cmd_up ;;
  down)   shift; cmd_down "${1:-}" ;;
  status) cmd_status ;;
  logs)   shift; cmd_logs "${1:-backend}" ;;
  backup) cmd_backup ;;
  *)      echo "Использование: scripts/dev.sh [up|down [--all]|status|logs <сервис>|backup]"; exit 1 ;;
esac
