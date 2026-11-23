#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.nginx.yml}"
WEB_ROOT="${WEB_ROOT:-$ROOT/web}"
WEB_IMAGE="${WEB_IMAGE:-md-web:latest}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Нет файла настроек: $ENV_FILE" >&2
  echo "Скопируйте .env.prod.example в .env.prod и заполните." >&2
  exit 1
fi

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

env_value() {
  # Значение KEY=... из env-файла, без кавычек.
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -1 | sed -e 's/^"//' -e 's/"$//'
}

build_web_host() {
  echo "==> Сборка фронтенда на хосте (pnpm)"
  (
    cd "$ROOT/frontend"
    export CI=1
    export NUXT_TELEMETRY_DISABLED=1
    export NUXT_PUBLIC_CAFE_APP_URL="$(env_value NUXT_PUBLIC_CAFE_APP_URL)"
    export NUXT_PUBLIC_LANDING_URL="$(env_value NUXT_PUBLIC_LANDING_URL)"

    if [[ ! -d node_modules ]]; then
      pnpm install --frozen-lockfile
    fi

    pnpm --filter @md/admin exec nuxt generate
    pnpm --filter @md/cafe exec nuxt generate
    pnpm --filter @md/landing exec nuxt generate
  )

  echo "==> Распаковка статики в $WEB_ROOT"
  mkdir -p "$WEB_ROOT"
  rm -rf "$WEB_ROOT/landing" "$WEB_ROOT/admin" "$WEB_ROOT/cafe"
  cp -a "$ROOT/frontend/apps/landing/.output/public" "$WEB_ROOT/landing"
  cp -a "$ROOT/frontend/apps/admin/.output/public" "$WEB_ROOT/admin"
  cp -a "$ROOT/frontend/apps/cafe/.output/public" "$WEB_ROOT/cafe"
  chmod -R a+rX "$WEB_ROOT"
}

build_web_docker() {
  local cafe_url landing_url
  cafe_url="$(env_value NUXT_PUBLIC_CAFE_APP_URL)"
  landing_url="$(env_value NUXT_PUBLIC_LANDING_URL)"

  echo "==> Сборка фронтенда в Docker"
  docker build \
    -t "$WEB_IMAGE" \
    --build-arg "NUXT_PUBLIC_CAFE_APP_URL=$cafe_url" \
    --build-arg "NUXT_PUBLIC_LANDING_URL=$landing_url" \
    "$ROOT/frontend"

  echo "==> Распаковка статики в $WEB_ROOT"
  docker rm -f md-web-extract >/dev/null 2>&1 || true
  docker create --name md-web-extract "$WEB_IMAGE" >/dev/null
  mkdir -p "$WEB_ROOT"
  rm -rf "$WEB_ROOT/landing" "$WEB_ROOT/admin" "$WEB_ROOT/cafe"
  docker cp md-web-extract:/srv/landing "$WEB_ROOT/landing"
  docker cp md-web-extract:/srv/admin "$WEB_ROOT/admin"
  docker cp md-web-extract:/srv/cafe "$WEB_ROOT/cafe"
  docker rm -f md-web-extract >/dev/null
  chmod -R a+rX "$WEB_ROOT"
}

build_web() {
  # На маленьком VPS Docker Hub часто недоступен: если есть Node и pnpm,
  # собираем статику прямо на хосте.
  if command -v pnpm >/dev/null 2>&1 && [[ -d "$ROOT/frontend/node_modules" ]]; then
    build_web_host
  else
    build_web_docker
  fi
}

install_nginx() {
  echo "==> Установка конфига Nginx"
  install -m 644 "$ROOT/deploy/nginx/myasnaya-derevnya.conf" \
    /etc/nginx/sites-available/myasnaya-derevnya.conf
  ln -sf /etc/nginx/sites-available/myasnaya-derevnya.conf \
    /etc/nginx/sites-enabled/myasnaya-derevnya.conf
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable --now nginx
  systemctl reload nginx
}

install_fail2ban() {
  echo "==> Установка конфига fail2ban"
  install -m 644 "$ROOT/deploy/fail2ban/jail.local" /etc/fail2ban/jail.local
  install -m 644 "$ROOT/deploy/fail2ban/filter.d/nginx-md-api.conf" \
    /etc/fail2ban/filter.d/nginx-md-api.conf
  systemctl enable --now fail2ban
  systemctl restart fail2ban
  fail2ban-client status
}

usage() {
  cat <<'EOF'
Использование: scripts/server-deploy.sh <команда>

  up             собрать бэкенд и фронтенд, поднять стек, обновить статику
  start          поднять уже собранные образы (без сборки)
  down           остановить стек (данные и медиа сохраняются)
  ps             статус контейнеров
  logs [s]       логи (сервис: backend, postgres, migrate)
  migrate        выполнить миграции вручную
  web            пересобрать только фронтенд и обновить статику
  backup         бэкап БД и медиа
  config         проверить compose-файл
  install-nginx  установить конфиг Nginx и перезагрузить его
  install-fail2ban установить конфиг fail2ban и перезапустить его

Перед первым запуском: cp .env.prod.example .env.prod && заполнить .env.prod
EOF
}

case "${1:-}" in
  up)
    compose up -d --build
    build_web
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
  web)
    build_web
    ;;
  backup)
    ENV_FILE="$ENV_FILE" COMPOSE_FILE="$COMPOSE_FILE" "$ROOT/scripts/backup.sh"
    ;;
  config)
    compose config
    ;;
  install-nginx)
    install_nginx
    ;;
  install-fail2ban)
    install_fail2ban
    ;;
  *)
    usage
    exit 1
    ;;
esac
