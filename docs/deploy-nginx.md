# Прод на одном сервере: Docker Compose + системный Nginx

Вариант [`deploy.md`](deploy.md), но без Caddy: статику трёх приложений
отдаёт Nginx, установленный на хосте, он же проксирует API и медиа в
контейнер бэкенда. Дополнительно ставится fail2ban.

## Что получится

| Адрес | Что |
|---|---|
| `http://<ip>/` | лендинг |
| `https://myasnaya-derevnya.ru` | лендинг |
| `https://team.myasnaya-derevnya.ru` | админка |
| `https://cafe.myasnaya-derevnya.ru` | кафе |
| `https://api.myasnaya-derevnya.ru` | API |

Контейнеры: `postgres`, одноразовый `migrate`, `backend` (порт `8000`
опубликован только на `127.0.0.1`). Nginx ходит в бэкенд локально.

## 1. Подготовка сервера

Ubuntu 24.04:

```bash
apt-get update
apt-get install -y docker.io docker-compose-v2 nginx fail2ban \
  certbot python3-certbot-nginx ufw rsync git curl ca-certificates

# 4 ГБ swap: сборка фронтенда на 2 ГБ RAM без него падает.
swapoff /swapfile 2>/dev/null || true
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## 2. Код и настройки

```bash
git clone <repo> /opt/myasnaya-derevnya
cd /opt/myasnaya-derevnya
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Заполните `.env.prod`:

1. `DB_PASSWORD` — `openssl rand -hex 24`.
2. `LOGIN_CODE_SECRET` — `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. `INITIAL_ADMIN_PASSWORD` — сильный пароль первого администратора.
4. `LANDING_HOST`, `ADMIN_HOST`, `CAFE_HOST`, `API_HOST` — домены без `https://`.
5. `NUXT_PUBLIC_LANDING_URL`, `NUXT_PUBLIC_CAFE_APP_URL` — полные `https://`
   адреса (вшиваются в статику при сборке).
6. `CORS_ORIGINS` — те же адреса в JSON-массиве.

Проверка:

```bash
scripts/server-deploy.sh config >/dev/null && echo OK
```

## 3. Запуск

```bash
scripts/server-deploy.sh up
```

Скрипт собирает образ бэкенда, поднимает `postgres` → `migrate` → `backend`,
собирает фронтенд и распаковывает статику в `web/`.

Установка системных конфигов (один раз):

```bash
scripts/server-deploy.sh install-nginx
scripts/server-deploy.sh install-fail2ban
> ВНИМАНИЕ: install-nginx перезаписывает конфиг из deploy/nginx и стирает правки certbot — после него повторно запустите certbot --nginx (раздел 5).
```

Проверка:

```bash
scripts/server-deploy.sh ps
curl -fsS http://127.0.0.1:8000/health
curl -fsS -H Host:api.myasnaya-derevnya.ru http://127.0.0.1/ready
curl -fsS https://team.myasnaya-derevnya.ru/ | head
fail2ban-client status
fail2ban-client status sshd
```

## 4. Первый вход
1. Откройте https://team.myasnaya-derevnya.ru.

2. Войдите под `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`.
3. Сразу смените пароль в шапке.

В проде отключены `/docs`, `/redoc` и `/openapi.json` (`DEBUG=False`).

## 5. Домен и HTTPS

Когда A-записи `myasnaya-derevnya.ru`, `www`, `team`, `cafe`, `api` укажут
на сервер:

```bash
certbot --nginx \
  -d myasnaya-derevnya.ru -d www.myasnaya-derevnya.ru \
  -d team.myasnaya-derevnya.ru \
  -d cafe.myasnaya-derevnya.ru \
  -d api.myasnaya-derevnya.ru
```

Certbot добавит `listen 443 ssl` в блоки из
`deploy/nginx/myasnaya-derevnya.conf` и настроит продление (`certbot.timer`).
После этого порты `8080:8082` можно закрыть:

```bash
ufw delete allow 8080:8082/tcp
```

## 6. Обновление

```bash
cd /opt/myasnaya-derevnya
scripts/server-deploy.sh backup
git pull --ff-only
scripts/server-deploy.sh up
```

Если сервер собирает из локальной копии (репозиторий ещё не запушен),
синхронизируйте код `rsync`-ом и запустите тот же `up`.

## 7. Бэкапы

```bash
scripts/server-deploy.sh backup
```

Ежедневный cron (`/etc/cron.d/md-backup`):

```cron
0 3 * * * root cd /opt/myasnaya-derevnya && ./scripts/server-deploy.sh backup >> /var/log/md-backup.log 2>&1
```

## 8. Диагностика

```bash
scripts/server-deploy.sh ps
scripts/server-deploy.sh logs backend
tail -f /var/log/nginx/md-api-error.log
nginx -t
fail2ban-client status nginx-md-api
```

| Симптом | Что смотреть |
|---|---|
| `502` на `/api` | `scripts/server-deploy.sh logs backend`, `curl 127.0.0.1:8000/ready` |
| Белый экран админки | `web/admin/index.html` существует; `md-admin-error.log` |
| Картинки 404 | `docker volume inspect` и `ls` в контейнере `/app/media` |
| Nginx не стартует | `nginx -t`, пути в `deploy/nginx/myasnaya-derevnya.conf` |
| fail2ban не банит | `fail2ban-client status nginx-md-api`, формат `/var/log/nginx/md-api-access.log` |
