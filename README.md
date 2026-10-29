# Мясная деревня

Учёт и продажи для мясного производства, магазинов и кафе: склад, производство,
каталог и цены, заказы, клиенты, сотрудники и права, фискальные чеки ОФД,
интеграция с кассами DoKa.

Проект — модульный монолит на **FastAPI + PostgreSQL** и три приложения на
**Nuxt 4**: рабочее место (админка), витрина кафе и лендинг.

---

## Что умеет

### Склад
- Поступления с партиями, сроками годности и себестоимостью.
- Списания, перемещения между точками, инвентаризации.
- Остатки, партии, журнал движений.
- Проведение продаж со списанием по средней себестоимости.

### Производство
- Техкарты: компоненты, выходы, потери, версии и дата действия.
- Производственные задания: черновик → проведение → списание сырья и приход
  готовой продукции с распределением себестоимости.

### Каталог и цены
- Категории, номенклатура, единицы измерения, фото и описания.
- Прайс-листы, цены и привязка прайс-листа к точке.
- Витрина кафе: позиции с ценой в прайс-листе точки.

### Заказы и кафе
- Корзина, оформление заказа, самовывоз, статусы заказа.
- Клиенты, вход по коду из SMS/логов (см. ограничения).
- Себестоимость проданных позиций.

### Сотрудники и права
- Сотрудники, роли, назначения ролей на подразделения.
- Права проверяются на бэкенде на каждый запрос, с учётом области доступа
  (своё подразделение / все подразделения).
- `SUPER_ADMIN` — wildcard-роль.

### Кассы и фискальные чеки
- Реестр касс и история привязок к точкам.
- Загрузка чеков ОФД, сопоставление строк с номенклатурой, проведение по складу.

### Продажи DoKa
- Регистрация касс DoKa, привязка к складу, ключи агентов.
- Приём чеков от C#-агента, идемпотентность, разметка товаров.
- Списание по техкартам для кафе: продажа блюда разворачивается в ингредиенты.
- Возвраты сохраняются, но по складу пока не проводятся.

---

## Технологии

| Слой | Что используется |
|---|---|
| Бэкенд | Python 3.14, FastAPI, SQLAlchemy Core 2.1, Alembic, PostgreSQL 17 |
| DI и транзакции | Dishka, собственный `TransactionManager` |
| Авторизация | пароль + сессия (Bearer UUID), роли и права, Argon2 |
| Фронтенд | Nuxt 4, Vue 3, TypeScript, Element Plus, pnpm |
| API-типы | OpenAPI → `openapi-typescript` (`@md/api-client`) |
| Инфраструктура | Docker Compose, Caddy, `uv` |

---

## Структура репозитория

```
.
├── src/myasnaya_derevnya/
│   ├── core/                 настройки, БД, DI, логи, медиа, seed
│   ├── modules/
│   │   ├── auth/             вход сотрудников и клиентов, сессии
│   │   ├── business/         организационная структура
│   │   ├── staff/            сотрудники, роли, права
│   │   ├── catalog/          категории, номенклатура, цены
│   │   ├── inventory/        склад и документы
│   │   ├── production/       техкарты и производственные задания
│   │   ├── orders/           заказы и корзина
│   │   ├── customer/         клиенты и их заказы
│   │   ├── fiscal/           кассы и чеки ОФД
│   │   └── pos/              импорт продаж DoKa
│   └── cli/                  консольные команды
├── migrations/               Alembic
├── tests/                    pytest, включая DB-тесты
├── frontend/
│   ├── apps/admin/           рабочее место (SPA)
│   ├── apps/cafe/            витрина кафе (SPA)
│   ├── apps/landing/         лендинг (SSR/статика)
│   └── packages/             api-client и money
├── scripts/                  dev/prod/backup
├── docs/                     deploy и ТЗ агента DoKa
├── Dockerfile                бэкенд
├── docker-compose.yml        локальная инфраструктура
├── docker-compose.prod.yml   прод-стек
└── .env.example              шаблон локальных настроек
```

---

## Быстрый старт (разработка)

### Что нужно

- Python **3.14** и [uv](https://docs.astral.sh/uv/)
- Node.js **22+** (проверено на 24) и **pnpm 11+** (лучше 12)
- Docker и Docker Compose

### Установка

```bash
git clone <repo> myasnaya-derevnya
cd myasnaya-derevnya

cp .env.example .env
# обязательно заполните LOGIN_CODE_SECRET (минимум 16 символов):
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

uv sync --all-groups
cd frontend && pnpm install && cd ..
```

### Запуск всего стека

```bash
scripts/dev.sh up
```

Скрипт поднимает PostgreSQL в Docker, применяет миграции и запускает API и все
три фронтенда.

| Что | Адрес |
|---|---|
| API и Swagger | http://127.0.0.1:8000/docs |
| Админка | http://127.0.0.1:3000 |
| Лендинг | http://127.0.0.1:3001 |
| Кафе | http://127.0.0.1:3002 |

Первый администратор — `admin` / `admin` из `.env` (обязательно смените пароль).

Управление:

```bash
scripts/dev.sh status
scripts/dev.sh logs backend
scripts/dev.sh logs admin
scripts/dev.sh down          # остановить сервисы, Postgres оставить
scripts/dev.sh down --all    # остановить и Postgres
scripts/dev.sh backup        # дамп БД
```

### Запуск по частям

```bash
# только БД и миграции
docker compose up -d postgres
DB_HOST=localhost .venv/bin/alembic upgrade head

# бэкенд
DB_HOST=localhost .venv/bin/uvicorn \
  --factory myasnaya_derevnya.main:create_app \
  --host 127.0.0.1 --port 8000

# фронтенд (из frontend/)
pnpm dev:admin      # 3000
pnpm dev:landing    # 3001
pnpm dev:cafe       # 3002
```

`.env` из репозитория содержит `DB_HOST=postgres` — это имя сервиса в Docker.
При запуске бэкенда на хосте всегда переопределяйте `DB_HOST=localhost`.

---

## Переменные окружения

Все настройки читаются из `.env` в корне репозитория. Основные:

| Переменная | Назначение |
|---|---|
| `DEBUG` | `True` в разработке; в проде `False` (отключает `/docs` и `/openapi.json`) |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_DATABASE` | PostgreSQL |
| `INITIAL_ADMIN_USERNAME`, `INITIAL_ADMIN_PASSWORD` | первый администратор |
| `ADMIN_ROLE_CODE`, `ADMIN_ROLE_NAME` | системная роль администратора |
| `LOGIN_CODE_SECRET` | HMAC-секрет кодов входа, обязателен, ≥ 16 символов |
| `MEDIA_ROOT`, `MEDIA_URL_PREFIX` | каталог и URL медиа |
| `MEDIA_MAX_BYTES`, `MEDIA_MAX_SIDE`, `MEDIA_WEBP_QUALITY` | обработка изображений |
| `LOG_LEVEL`, `LOG_JSON`, `LOG_ACCESS` | логирование |
| `OFD_API_URL`, `OFD_API_TOKEN`, `OFD_INN`, `OFD_TIMEZONE` | интеграция ОФД |
| `OFD_CUTOVER_DATE` | не загружать чеки ОФД раньше даты |
| `CORS_ORIGINS` | JSON-массив источников (нужен только при разных доменах) |

Прод-настройки и домены описаны в `.env.prod.example` и
[`docs/deploy.md`](docs/deploy.md).

---

## Команды разработчика

### Бэкенд

```bash
uv run ruff check .                 # линтер (обязательный gate)
uv run pytest                       # все тесты
uv run pytest -m "not db"           # без PostgreSQL
uv run pytest tests/modules/catalog -q
```

Тесты БД требуют PostgreSQL и отдельную базу:

```bash
docker exec md-postgres createdb -U user myasnaya_derevnya_test   # если её ещё нет
DB_HOST=localhost DB_DATABASE=myasnaya_derevnya_test \
  .venv/bin/alembic upgrade head
uv run pytest
```

Миграции:

```bash
DB_HOST=localhost .venv/bin/alembic upgrade head
DB_HOST=localhost .venv/bin/alembic revision --autogenerate -m "описание"
DB_HOST=localhost .venv/bin/alembic check
```

Новые таблицы обязательно импортируйте в `migrations/env.py`, иначе
autogenerate их не увидит.

### Фронтенд (из `frontend/`)

```bash
pnpm dev:admin
pnpm typecheck:admin
pnpm build:admin

pnpm dev:cafe
pnpm typecheck:cafe
pnpm build:cafe

pnpm dev:landing
```

Типы API генерируются из запущенного бэкенда (нужен `DEBUG=True`):

```bash
pnpm api:types
```

`frontend/packages/api-client/src/schema.d.ts` — сгенерированный файл, руками
не правится.

### Демо-данные

```bash
DB_HOST=localhost uv run python scripts/seed_demo.py
```

Нужен запущенный API (по умолчанию `http://127.0.0.1:8000`, можно передать
`--api-url`). Создаёт подразделения, категории, номенклатуру, техкарты, остатки, меню кафе,
роли и сотрудников (пароль `demo12345`). Скрипт идемпотентен; `--reset` удаляет
демо-данные и пересоздаёт структуру — **не запускать в проде**.

---

## Архитектура бэкенда

Модульный монолит. Каждый модуль повторяет одну структуру:

```
modules/<name>/
├── domain/          сущности, value objects, ошибки, permissions
├── application/     use case'ы (interactors), DTO, сервисы
├── infrastructure/  таблицы SQLAlchemy Core, репозитории, ридеры, DI
└── presentation/    FastAPI-роутеры и схемы, фасады для других модулей
```

Правила:

- **SQLAlchemy Core**, не ORM: таблицы описываются в `infrastructure/tables.py`.
- Межмодульные вызовы — только через фасады (`BusinessAPI`, `CatalogAPI`,
  `InventoryAPI`, `ProductionAPI`, `StaffAPI`, `AuthAPI`), не через внутренности.
- Запись — репозитории, чтение — ридеры.
- Use case получает Command/Query, проверяет права и вызывает репозитории.
- Коммит — через `TransactionManager`; ошибки БД превращаются в доменные.
- DI — Dishka; все interactor'ы регистрируются в
  `modules/<name>/infrastructure/dependencies.py`.
- Ошибки: `DomainError` → 400, `ValidationError` → 422, `Unauthorized` → 401,
  `Forbidden` → 403, `NotFound` → 404, `Conflict` → 409, остальное → 500.

### Модули и API

| Модуль | Префикс API | Ответственность |
|---|---|---|
| `auth` | `/api/auth` | вход сотрудников, сессии, смена пароля |
| `staff` | `/api/staff` | сотрудники, роли, права, области доступа |
| `business` | `/api/business` | организационная структура и складские локации |
| `catalog` | `/api/catalog` | категории, номенклатура, цены, фото, витрина |
| `inventory` | `/api/inventory` | склад, документы, остатки, движения |
| `production` | `/api/production` | техкарты и производственные задания |
| `orders` | `/api/orders`, `/api/me` | заказы, корзина, статусы |
| `customer` | `/api/customers` | профили и вход клиентов |
| `fiscal` | `/api/fiscal` | кассы, привязки, чеки ОФД |
| `pos` | `/api/pos` | источники DoKa, агенты, чеки, разметка |

Схемы БД: `auth`, `staff`, `business`, `catalog`, `inventory`, `production`,
`orders`, `fiscal`, `pos`.

### Авторизация и права

- Сотрудник: `Authorization: Bearer <session-uuid>` — сырой UUID сессии, не JWT.
- Клиент кафе: отдельная сессия, вход по одноразовому коду.
- Целевое подразделение всегда передаётся явно (`org_unit_id` в body/path или
  query при чтении); проверка — `can(permission, org_unit_id)`.
- Права объявлены в `modules/<name>/domain/permissions.py` и агрегируются в
  `core/permissions.py`. Новое право нужно добавить и в
  `frontend/apps/admin/app/utils/access.ts`; тест `tests/test_access_map.py`
  это проверяет.

### Логирование и медиа

- Логи в stdout: обычный текст в dev, JSON в проде (`LOG_JSON=True`).
- `X-Request-ID` и `user_id` автоматически попадают в каждую запись.
- Бизнес-события логируются в application-слое.
- Файлы лежат на диске (`MEDIA_ROOT`), в БД только ссылки. При загрузке
  изображения сжимаются и перекодируются в WEBP.

---

## Продажи DoKa

Схема:

1. На кассе Windows крутится C#-агент, читает журнал
   `Обмен_Продаж_*.xml`, который выгружает DoKa.
2. Агент отправляет чеки на `POST /api/pos/receipts` с ключом терминала.
3. Сервер сохраняет чек и строки, применяет разметку товаров и проводит продажу
   по складу.
4. Если номенклатура — главный выход техкарты, списываются ингредиенты
   (кафе); иначе списывается сама позиция.
5. Возвраты сохраняются как `ignored`; в v1 нет движения `RETURN`.

Админка: раздел **«Продажи DoKa»** — чеки, кассы и агенты, разметка товаров.
ТЗ агента и HTTP-контракт: [`docs/pos-agent.md`](docs/pos-agent.md).

---

## Продакшн

Подробный runbook: [`docs/deploy.md`](docs/deploy.md).

Коротко:

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
# заполнить домены, пароли, LOGIN_CODE_SECRET, INITIAL_ADMIN_PASSWORD

scripts/prod.sh up
```

Что поднимается:

- PostgreSQL (наружу не публикуется);
- миграции Alembic;
- FastAPI (healthcheck `/ready`, наружу не публикуется);
- Caddy: лендинг, админка, кафе, API; автоматический TLS и прокси `/api`,
  `/media`.

Команды:

```bash
scripts/prod.sh ps
scripts/prod.sh logs backend
scripts/prod.sh backup
scripts/prod.sh down
```

Медиа хранятся в Docker volume и попадают в бэкап вместе с БД. CI/CD пока нет:
обновление — `git pull` + `scripts/prod.sh up` (миграции применяются
автоматически).

---

## Тесты и проверки

```bash
uv run ruff check .
uv run pytest

cd frontend
pnpm typecheck:admin
pnpm build:admin
pnpm test
```

- `tests/core` — настройки, логи, обработка ошибок, транзакции.
- `tests/modules` — домен, use case'ы, API и DB-интеграции.
- `pytest -m "not db"` не требует PostgreSQL.
- `tests/test_permissions.py` и `tests/test_access_map.py` следят за
  согласованностью прав.

---

## Текущие ограничения

- C#-агент сбора продаж DoKa ещё не написан; бэкенд и контракт готовы.
- Нет SMS-провайдера: в проде коды входа клиентов не отправляются, поэтому
  онлайн-заказы кафе пока не запускать.
- Нет массового импорта номенклатуры, цен и остатков; GTIN/штрихкоды в форме
  номенклатуры не редактируются.
- Нет онлайн-оплаты и доставки.
- Нет CI/CD: сборка, миграции и бэкапы запускаются на сервере вручную.
- Один сервер: горизонтального масштабирования и объектного хранилища медиа нет.

---

## Документация

- [`docs/deploy.md`](docs/deploy.md) — деплой на один сервер, бэкапы, обновления.
- [`docs/pos-agent.md`](docs/pos-agent.md) — ТЗ и HTTP-контракт агента DoKa.
- [`frontend/README.md`](frontend/README.md) — как устроена админка и её страницы.
- [`AGENTS.md`](AGENTS.md) — правила разработки и архитектурные соглашения.
