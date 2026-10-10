from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

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
from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.modules.auth.presentation.api.v1.endpoints import (
    login_router,
    logout_router,
)
from myasnaya_derevnya.modules.business.presentation.api.v1 import (
    router as business_router,
)
from myasnaya_derevnya.modules.catalog.presentation.api.v1 import (
    router as catalog_router,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1 import router as staff_router

STATUS_BY_CATEGORY: dict[type[AppError], int] = {
    ValidationError: 422,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
}


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:

    if not isinstance(exc, ProjectError):
        return JSONResponse(
            status_code=500, content={"message": "Internal server error"}
        )

    if isinstance(exc, DomainError):
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

    return JSONResponse(
        status_code=status_code,
        content={"error": type(exc).__name__, "message": str(exc)},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_system()
    yield


def include_routers(app: FastAPI) -> None:
    app.include_router(login_router)
    app.include_router(logout_router)
    app.include_router(staff_router)
    app.include_router(business_router)
    app.include_router(catalog_router)


def create_app() -> FastAPI:
    api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)
    app = FastAPI(lifespan=lifespan, dependencies=[Depends(api_key_scheme)])

    app.add_exception_handler(ProjectError, api_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,  # Разрешить передавать куки и заголовки авторизации
        allow_methods=["*"],  # Разрешить все HTTP методы (GET, POST, PUT, DELETE...)
        allow_headers=["*"],  # Разрешить все заголовки
    )

    include_routers(app)

    return app


def main() -> None:
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
