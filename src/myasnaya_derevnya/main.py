from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from myasnaya_derevnya.core.errors import AppError
from myasnaya_derevnya.modules.auth.presentation.api.v1.endpoints import login_router
from myasnaya_derevnya.modules.organization.presentation.api.v1.endpoints import (
    router as organization_router,
)


async def api_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):

    yield


def include_routers(app: FastAPI, api_key_scheme: APIKeyHeader) -> None:
    app.include_router(login_router, dependencies=[Depends(api_key_scheme)])
    app.include_router(organization_router, dependencies=[Depends(api_key_scheme)])


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.add_exception_handler(AppError, api_exception_handler)

    api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,  # Разрешить передавать куки и заголовки авторизации
        allow_methods=["*"],  # Разрешить все HTTP методы (GET, POST, PUT, DELETE...)
        allow_headers=["*"],  # Разрешить все заголовки
    )

    include_routers(app, api_key_scheme)

    return app


def main() -> None:
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
