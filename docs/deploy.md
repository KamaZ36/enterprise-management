# Продакшн на одном сервере (Docker Compose, без CI/CD)

Инструкция для ручного развёртывания на одном VPS. Всё собирается и
запускается командами на сервере; CI/CD не используется.

## Что получится

Один сервер, один `docker compose`:

- `postgres` — PostgreSQL 17, наружу не публикуется;
- `migrate` — одноразовый прогон `alembic upgrade head`;
- `backend` — FastAPI на Uvicorn;
- `web` — Caddy: три статических приложения (лендинг, кафе, админка) и
  проксирование API, автоматический HTTPS.

Четыре адреса (пример):

| Адрес | Что |
|---|---|
| `https://example.com` | лендинг |
| `https://admin.example.com` | админка |
| `https://cafe.example.com` | кафе |
| `https://api.example.com` | API, сюда ходит агент DoKa |

## Требования

- Ubuntu/Debian VPS, 2 vCPU, 4 ГБ RAM, 40 ГБ SSD.
- Docker Engine 27+ и Docker Compose v2.
- DNS: A-записи `@`, `admin`, `cafe`, `api` указывают на IP сервера.
- Открыты только порты 22, 80, 443.

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Порты `5432` и `8000` наружу не открываются: база и бэкенд доступны только
внутри compose-сети.

## 1. Подготовка

```bash
git clone <repo> /opt/myasnaya-derevnya
cd /opt/myasnaya-derevnya
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Заполните `.env.prod`:

1. `DB_PASSWORD` — сгенерируйте: `openssl rand -hex 24`.
2. `LOGIN_CODE_SECRET` — сгенерируйте:
   `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
3. `INITIAL_ADMIN_PASSWORD` — придумайте сильный пароль. После первого входа
   его всё равно нужно сменить.
4. `LANDING_HOST`, `ADMIN_HOST`, `CAFE_HOST`, `API_HOST` — ваши домены без
   `https://`.
5. `NUXT_PUBLIC_LANDING_URL`, `NUXT_PUBLIC_CAFE_APP_URL` — полные `https://`
   адреса. Они вшиваются в статику при сборке.
6. `CORS_ORIGINS` — те же адреса в JSON-массиве.

Проверить, что compose видит настройки:

```bash
scripts/prod.sh config >/dev/null && echo OK
```

## 2. Запуск

```bash
scripts/prod.sh up
```

Что произойдёт:

1. Соберутся образы бэкенда и фронтенда (несколько минут).
2. Поднимется PostgreSQL и пройдут миграции.
3. Запустится API, затем Caddy.
4. Caddy получит TLS-сертификаты Let's Encrypt (нужны DNS и открытые 80/443).

Проверка:

```bash
scripts/prod.sh ps
scripts/prod.sh logs web
curl -fsS https://api.example.com/health
curl -fsS https://api.example.com/ready
```

`/health` — процесс жив; `/ready` — жива и база.

## 3. Первый вход

1. Откройте `https://admin.example.com`.
2. Войдите под `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`.
3. Сразу смените пароль: кнопка «Сменить пароль» в шапке.

В проде отключены `/docs`, `/redoc` и `/openapi.json` (включаются только при
`DEBUG=True`).

## 4. Первичное наполнение

Автоматически создаются только корневое подразделение, роль `SUPER_ADMIN` и
первый администратор. Остальное заводится в админке:

1. **Организация** — магазины, кафе, производство.
2. **Категории** — группы номенклатуры.
3. **Номенклатура** — название, артикул, единица, категория, фото, описание.
   Пока только по одной позиции: массового импорта CSV/XLSX нет.
4. **Прайс-листы и цены** — создайте прайс-лист, задайте цены, привяжите
   прайс-лист к точке. Без цены позиция не попадёт на витрину кафе.
5. **Начальные остатки** — через инвентаризацию (вручную построчно).
6. **Техкарты** — для списания кафе по ингредиентам.
7. **Роли и сотрудники** — кассир, менеджер, мастер цеха и т.д.
8. **Кассы DoKa** — раздел «Продажи DoKa»: зарегистрируйте кассу, привяжите
   склад, выдайте ключ агенту, сопоставьте товары.

Ограничения текущей версии: GTIN/штрихкоды в форме номенклатуры не
редактируются, массового импорта и массовой разметки нет. Это следующие
задачи после запуска.

## 5. Обновление версии

Перед обновлением сделайте бэкап:

```bash
scripts/prod.sh backup
cd /opt/myasnaya-derevnya
git pull --ff-only
scripts/prod.sh up
```

`migrate` выполнится автоматически. Если миграция упадёт, backend не
запустится — смотрите `scripts/prod.sh logs migrate`.

Откат кода: `git checkout <предыдущий-тег>` и снова `scripts/prod.sh up`.
Миграции в этой схеме вперёд-совместимые; если откат требует отката БД —
восстанавливайте бэкап.

## 6. Бэкапы

```bash
scripts/prod.sh backup
```

Создаёт в `backups/`:

- `db-YYYYMMDD-HHMMSS.sql.gz` — дамп PostgreSQL;
- `media-YYYYMMDD-HHMMSS.tgz` — фото номенклатуры и меню.

Хранится 14 последних пар. Изменить: `BACKUP_KEEP=30 scripts/prod.sh backup`.

Ежедневный cron:

```cron
0 3 * * * cd /opt/myasnaya-derevnya && ENV_FILE=.env.prod ./scripts/backup.sh >> /var/log/md-backup.log 2>&1
```

Обязательно копируйте `backups/` и `.env.prod` на другой носитель
(`rsync`, `rclone`, второй сервер). Бэкап на том же диске не спасает от
потери сервера.

### Восстановление БД

Остановите приложение, чтобы никто не писал в базу:

```bash
scripts/prod.sh down
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d postgres
gunzip -c backups/db-XXXX.sql.gz \
  | docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T postgres \
      sh -c 'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v ON_ERROR_STOP=1'
scripts/prod.sh up
```

### Восстановление медиа

```bash
scripts/prod.sh up
cat backups/media-XXXX.tgz \
  | docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T backend \
      tar -xzf - -C /app
```

## 7. Диагностика

```bash
scripts/prod.sh ps
scripts/prod.sh logs backend
scripts/prod.sh logs web
scripts/prod.sh logs migrate
scripts/prod.sh exec backend bash
scripts/prod.sh exec postgres sh -c 'psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"'
```

Типовые проблемы:

| Симптом | Что смотреть |
|---|---|
| Caddy не получает сертификат | DNS ещё не разошёлся, закрыты 80/443, `logs web` |
| `502` на странице | backend не healthy: `logs backend`, `curl /ready` |
| Картинки 404 | `exec backend ls /app/media`, volume `media_data` |
| Ошибка пароля БД | `.env.prod` и пароль внутри уже созданного volume; меняйте `ALTER USER` или пересоздавайте volume (с потерей данных) |
| Сборка падает | место на диске: `df -h`, `docker system prune` |

## 8. Ограничения этой конфигурации

- **Нет CI/CD**: сборка и обновление запускаются вручную на сервере.
- **Нет SMS-провайдера**: вход клиента в кафе/лендинге в проде не работает
  (код входа только пишется в лог при `DEBUG=True`). Онлайн-заказы кафе до
  подключения SMS не включать.
- **Нет онлайн-оплаты и доставки** — в разработке.
- **Нет массового импорта номенклатуры/цен/остатков** — только ручной ввод.
- Один сервер: горизонтального масштабирования и внешнего объектного
  хранилища нет; медиа живут в Docker volume.
