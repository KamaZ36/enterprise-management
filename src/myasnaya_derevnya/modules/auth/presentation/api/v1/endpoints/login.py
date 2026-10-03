from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordCommand,
    LoginByPasswordInteractor,
)

router = APIRouter(prefix="/api/login", tags=["Аутентификация"])


@router.post("/password", description="Аутентификация по паролю (Для сотрудников)")
async def login_by_password(request: Request, command: LoginByPasswordCommand):
    async with container(context={Request: request}) as context:
        interactor = await context.get(LoginByPasswordInteractor)
        session = await interactor(command)

    return JSONResponse(content={"session": session})
