from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.auth.application.interactors.change_password import (
    ChangePasswordCommand,
    ChangePasswordInteractor,
)

router = APIRouter(prefix="/api/me", tags=["Аутентификация"])

MIN_PASSWORD_LENGTH = 8


class ChangePasswordSchema(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


@router.post("/password", description="Сменить свой пароль")
async def change_password(request: Request, data: ChangePasswordSchema) -> JSONResponse:
    command = ChangePasswordCommand(
        current_password=data.current_password,
        new_password=data.new_password,
    )

    async with container(context={Request: request}) as context:
        interactor = await context.get(ChangePasswordInteractor)
        await interactor(command)

    return JSONResponse(content={"message": "ok!"})
