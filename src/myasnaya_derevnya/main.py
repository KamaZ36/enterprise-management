from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from myasnaya_derevnya.modules.auth.presentation.api.v1.endpoints import login_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def include_routers(app: FastAPI) -> None:
    app.include_router(login_router)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

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
