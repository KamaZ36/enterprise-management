from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.auth.application.interactors.logout import (
    LogoutInteractor,
)

router = APIRouter(prefix="/api/logout", tags=["Аутентификация"])


@router.post("", description="Завершить текущую сессию")
async def logout(request: Request) -> JSONResponse:
    async with container(context={Request: request}) as context:
        interactor = await context.get(LogoutInteractor)
        await interactor()

    return JSONResponse(content={"message": "ok"})
