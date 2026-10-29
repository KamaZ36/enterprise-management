# AGENTS.md

Monorepo: FastAPI backend (`src/myasnaya_derevnya`, Python 3.14, managed by `uv`) plus a pnpm workspace of three Nuxt 4 apps (`frontend/apps/{admin,cafe,landing}`) and two TS packages (`frontend/packages/{api-client,money}`). Root `README.md` is empty; the useful prose is in `frontend/README.md` (Russian) and code comments.

## Commands

Backend (run from repo root; `.venv` has the package installed editable, so `.venv/bin/*` works without `PYTHONPATH`):
- Install: `uv sync --all-groups`
- Run API: `uv run uvicorn --factory myasnaya_derevnya.main:create_app --host 127.0.0.1 --port 8000`
- Lint (the gate): `uv run ruff check .` — passes clean. Do **not** run `ruff format .`; formatting is not enforced and it would churn ~54 unrelated files.
- Tests: `uv run pytest`; unit only `uv run pytest -m "not db"` (346 of 407); single `uv run pytest tests/modules/catalog/test_update_category.py -k update`.
- Migrations: `DB_HOST=localhost .venv/bin/alembic upgrade head`; new one `alembic revision --autogenerate -m "..."`.
- Full local stack (Docker Postgres + migrations + API + all 3 frontends): `scripts/dev.sh up`, then `scripts/dev.sh status | logs <backend|admin|landing|cafe> | down [--all]`. PIDs/logs live in `.tmp/dev/`.

Frontend (run from `frontend/`):
- Install: `pnpm install`
- Dev one app: `pnpm dev:admin` (3000), `dev:landing` (3001), `dev:cafe` (3002); typecheck `pnpm typecheck:admin`; build `pnpm build:admin` (typechecks first) / `build:cafe`.
- Tests: `pnpm test` (recursive; only `packages/money` has vitest).
- Regenerate API types after any backend route/schema change: `pnpm api:types` (fetches `API_URL`, default `http://127.0.0.1:8000`). `frontend/packages/api-client/src/schema.d.ts` is generated and committed — never edit it by hand.

## Backend architecture

Each module is `modules/<name>/{domain,application,infrastructure,presentation}` (auth, business, catalog, customer, inventory, production, orders, staff):
- `domain`: entities, value objects, `permissions.py`, `errors.py`.
- `application`: one file per use case in `interactors/`, plus `dto.py` and module errors.
- `infrastructure`: `tables.py` (SQLAlchemy **Core** tables, not ORM models), `repositories/<x>/{base,sqlalchemy}.py` for writes, `readers/<x>/{base,sqlalchemy}.py` for reads, `dependencies.py` (dishka providers).
- `presentation/api/v1/{endpoints,schemas}.py`. Cross-module calls go only through the other module's presentation API/facade (`StaffAPI`, `BusinessAPI`, `AuthAPI`), never its internals.

Endpoint pattern: build a Command/Query, then `async with container(context={Request: request}) as context: interactor = await context.get(X); await interactor(cmd)`. Every `context.get(X)` type must be registered in that module's `infrastructure/dependencies.py`, or `tests/test_smoke.py::test_every_endpoint_interactor_is_registered` fails. App wiring is in `src/myasnaya_derevnya/main.py` (`create_app` factory, `include_routers`).

Errors: raise subclasses of `ProjectError` (`core/errors.py`). `main.py` maps `DomainError`→400, `AppError` subclasses→422/401/403/404/409, everything else→500 with a generic message (details are not leaked). A new error category needs an entry in `STATUS_BY_CATEGORY`.

Auth: `Authorization: Bearer <session-uuid>` — a raw session UUID, not a JWT. There is no ambient request scope: the target org unit is always explicit — in the body/path on writes (e.g. `org_unit_id`, `warehouse_id`) and as an optional `org_unit_id` query filter on lists — and every check is `can(permission, org_unit_id)`.

Permissions: declared per module in `domain/permissions.py`, aggregated (sorted, unique) by `core/permissions.all_permissions()`. Tests enforce no duplicates, coverage of every module, and that the aggregate exactly equals the declared set. Interactors authorize via `StaffAPI.can_anywhere(...)`. Frontend permission codes in `frontend/apps/admin/app/utils/access.ts` must all exist in the registry (`tests/test_access_map.py`) — update it when adding a permission.

Settings: a single `AppSettings` reads `<repo>/.env` (copy `.env.example`). `LOGIN_CODE_SECRET` (min 16 chars) is required or the app won't start. `.env` ships `DB_HOST=postgres` (Docker service name) — host runs must override `DB_HOST=localhost`.

Logging: configured once in `create_app` via `core/logging/config.py::setup_logging(LoggingSettings())` (`LOG_LEVEL`, `LOG_JSON`, `LOG_ACCESS`). Console in dev, JSON in prod; stdout only, no file handlers. `RequestContextMiddleware` puts `X-Request-ID` into a contextvar and `IdentityProvider` binds `user_id`, so `ContextFilter` stamps `request_id`/`user_id` onto every record automatically. Business events are logged in the application layer (interactors) with `logging.getLogger(__name__).info("Событие", extra={"order_id": ...})`; both formatters render arbitrary `extra` fields (console as `key=value`, JSON as top-level fields, non-JSON values stringified), so do not pass clash-prone keys such as `name`/`module`/`message` (ruff `G101` enforces this). Reads are covered by the access log — log mutating use-cases and auth events, not queries. Access lines and 5xx tracebacks are logged there; 4xx/`DomainError` at INFO. Never log secrets (codes, passwords, `Authorization`); `LoggingLoginCodeSender` prints the code only when `DEBUG=true`.

Startup (`core/seed.py::bootstrap_system`, run in the app lifespan) seeds a root org unit, the `SUPER_ADMIN` role, and the initial admin from `INITIAL_ADMIN_*` (default admin/admin).

Media: files live on disk under `MEDIA_ROOT`, the DB stores only relative refs, served at `MEDIA_URL_PREFIX`. Uploads are resized/encoded to WEBP.

## Database & migrations

- Alembic builds its URL from settings; `alembic.ini`'s `sqlalchemy.url` is intentionally empty.
- `migrations/env.py` imports every `tables.py` explicitly (`# noqa: F401`) — add new tables there or autogenerate silently misses them.
- Shared `MetaData` with a naming convention (`core/database/metadata.py`); constraint names like `uq_nomenclatures_sku` are asserted in tests.
- `IntegrityError` is converted to `UniqueViolationError`/`ConflictError` by the transaction manager.

## Tests

- pytest with `asyncio_mode = "auto"` — do not add `@pytest.mark.asyncio`.
- `tests/conftest.py` sets env defaults; DB tests default to `DB_DATABASE=myasnaya_derevnya_test` on localhost.
- `pytestmark = pytest.mark.db` marks DB-backed tests; the `db_session` fixture (`tests/modules/conftest.py`) skips when Postgres is unreachable. Requires the schema migrated (run alembic against the test DB).
- DB cleanup uses `TRUNCATE` on inventory tables and deletion of `PYTEST-`-prefixed catalog rows (`tests/modules/helpers.py`).

## Frontend notes

- Nuxt 4, SSR disabled for admin, Element Plus. `nitro.devProxy` forwards `/api` and `/media` to the backend, so local requests are same-origin (no CORS).
- `@md/api-client` (openapi-fetch) is typed from the generated OpenAPI schema.
- Read `frontend/README.md` before touching the admin app: page pattern, `CAN.*` permissions, the required root `class="page"` for layout, and a troubleshooting table.
- `frontend/prototype/` is a static design reference (HTML + screenshots), not part of any build.
