#!/usr/bin/env bash
# Запуск всего проекта одной командой: база, миграции, бэкенд, админка, лендинг.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_DIR="$ROOT/.tmp/dev"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

BACKEND_PORT=8000
ADMIN_PORT=3000
LANDING_PORT=3001

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

wait_port() {
  local port="$1" name="$2" tries="${3:-60}"
  for ((i = 0; i < tries; i++)); do
    if port_open "$port"; then ok "$name на порту $port"; return 0; fi
    sleep 1
  done
  bad "$name не поднялся на порту $port — смотрите $LOG_DIR"
  return 1
}

# Порт открывается раньше, чем сервер готов отвечать: ждём именно ответ.
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
  say "База данных"
  docker compose up -d postgres >/dev/null
  wait_port 5432 "Postgres" 60 || return 1

  say "Миграции"
  TMPDIR="$ROOT/.tmp" DB_HOST=localhost .venv/bin/alembic upgrade head 2>&1 | tail -1
  ok "схема обновлена"

  say "Сервисы"
  start backend env TMPDIR="$ROOT/.tmp" DB_HOST=localhost \
    .venv/bin/uvicorn --factory myasnaya_derevnya.main:create_app \
    --host 127.0.0.1 --port "$BACKEND_PORT"
  wait_http "$BACKEND_PORT" "Бэкенд" /docs 90 || return 1

  frontend_env
  start admin pnpm --dir frontend/apps/admin dev
  start landing pnpm --dir frontend/apps/landing dev

  wait_http "$ADMIN_PORT" "Админка" / 150 || true
  wait_http "$LANDING_PORT" "Лендинг" / 150 || true

  say "Готово"
  printf '   Админка:  http://127.0.0.1:%s   (вход admin / admin)\n' "$ADMIN_PORT"
  printf '   Лендинг:  http://127.0.0.1:%s\n' "$LANDING_PORT"
  printf '   API:      http://127.0.0.1:%s/docs\n' "$BACKEND_PORT"
  printf '\n   Логи:     %s\n' "$LOG_DIR"
  printf '   Остановка: scripts/dev.sh down\n'
}

cmd_down() {
  say "Остановка сервисов"
  for name in landing admin backend; do
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
    docker compose stop postgres >/dev/null 2>&1 || true
    ok "Postgres остановлен"
  else
    printf '   · Postgres оставлен работать (остановить: scripts/dev.sh down --all)\n'
  fi
}

cmd_status() {
  say "Состояние"
  for pair in "backend:$BACKEND_PORT" "admin:$ADMIN_PORT" "landing:$LANDING_PORT"; do
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

case "${1:-up}" in
  up)     cmd_up ;;
  down)   shift; cmd_down "${1:-}" ;;
  status) cmd_status ;;
  logs)   shift; cmd_logs "${1:-backend}" ;;
  *)      echo "Использование: scripts/dev.sh [up|down [--all]|status|logs <сервис>]"; exit 1 ;;
esac
