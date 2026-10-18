import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from myasnaya_derevnya.core.errors import (
    AppError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ProjectError,
    UnauthorizedError,
    ValidationError,
)
from myasnaya_derevnya.core.logging import RequestContextMiddleware, setup_logging
from myasnaya_derevnya.core.logging.context import reset_request_id, set_request_id
from myasnaya_derevnya.core.media.paths import media_root
from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings.cors import CorsSettings
from myasnaya_derevnya.core.settings.logging import LoggingSettings
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.modules.auth.presentation.api.v1.endpoints import (
    login_router,
    logout_router,
    password_router,
)
from myasnaya_derevnya.modules.business.presentation.api.v1 import (
    router as business_router,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1 import (
    media_router as catalog_media_router,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1 import (
    router as catalog_router,
)
from myasnaya_derevnya.modules.customer.presentation.api.v1.customers import (
    router as customers_router,
)
from myasnaya_derevnya.modules.customer.presentation.api.v1.endpoints import (
    login_router as customer_login_router,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1 import (
    router as inventory_router,
)
from myasnaya_derevnya.modules.production.presentation.api.v1 import (
    router as production_router,
)
from myasnaya_derevnya.modules.sales.presentation.api.v1 import (
    router as sales_router,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1 import (
    access_router,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1 import (
    router as staff_router,
)

STATUS_BY_CATEGORY: dict[type[AppError], int] = {
    ValidationError: 422,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
}

logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ProjectError):
        return JSONResponse(
            status_code=500, content={"message": "Internal server error"}
        )

    if isinstance(exc, DomainError):
        logger.info("Нарушено доменное правило: %s: %s", type(exc).__name__, exc)
        return JSONResponse(
            status_code=400, content={"error": type(exc).__name__, "message": str(exc)}
        )

    status_code = next(
        (
            code
            for category, code in STATUS_BY_CATEGORY.items()
            if isinstance(exc, category)
        ),
        400,
    )

    logger.info("Отклонён запрос: %s: %s", type(exc).__name__, exc)

    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "message": str(exc)},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    token = set_request_id(request.scope.get("request_id"))
    try:
        logger.exception("Необработанная ошибка")
    finally:
        reset_request_id(token)
    return JSONResponse(status_code=500, content={"message": "Internal server error"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_system()
    yield


def include_routers(app: FastAPI) -> None:
    app.include_router(login_router)
    app.include_router(sales_router)
    app.include_router(logout_router)
    app.include_router(password_router)
    app.include_router(access_router)
    app.include_router(staff_router)
    app.include_router(business_router)
    app.include_router(catalog_router)
    app.include_router(catalog_media_router)
    app.include_router(inventory_router)
    app.include_router(production_router)
    app.include_router(customer_login_router)
    app.include_router(customers_router)


def include_media(app: FastAPI) -> None:
    settings = MediaSettings()
    root = media_root(settings)
    root.mkdir(parents=True, exist_ok=True)

    app.mount(settings.media_url_prefix, StaticFiles(directory=root), name="media")


def create_app() -> FastAPI:
    logging_settings = LoggingSettings()
    setup_logging(logging_settings)

    api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)
    app = FastAPI(lifespan=lifespan, dependencies=[Depends(api_key_scheme)])

    app.add_exception_handler(ProjectError, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CorsSettings().cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RequestContextMiddleware, enabled=logging_settings.log_access
    )

    include_routers(app)
    include_media(app)

    return app


def main() -> None:
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None, access_log=False)


if __name__ == "__main__":
    main()
