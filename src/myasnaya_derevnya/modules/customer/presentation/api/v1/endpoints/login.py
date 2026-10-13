from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.customer.application.commands import (
    LoginCustomerCommand,
    RequestLoginCodeCommand,
)
from myasnaya_derevnya.modules.customer.application.interactors.login_customer import (
    LoginCustomerInteractor,
)

router = APIRouter(prefix="/api/customers", tags=["Клиенты"])


@router.post("/login/code", description="Отправить код входа (для клиентов)")
async def request_login_code(request: Request, command: RequestLoginCodeCommand):
    async with container(context={Request: request}) as context:
        auth_api = await context.get(AuthAPI)
        await auth_api.request_login_code(command.phone)

    return JSONResponse(content={"sent": True})


@router.post("/login", description="Аутентификация по коду из СМС (для клиентов)")
async def login_customer(request: Request, command: LoginCustomerCommand):
    async with container(context={Request: request}) as context:
        interactor = await context.get(LoginCustomerInteractor)
        session = await interactor(command.phone, command.code)

    return JSONResponse(content={"session": str(session)})
