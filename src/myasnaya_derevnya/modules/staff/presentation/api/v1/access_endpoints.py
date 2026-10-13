from fastapi import APIRouter, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.staff.application.interactors.get_current_user import (
    GetCurrentUserInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_permissions import (
    ListPermissionsInteractor,
)
from myasnaya_derevnya.modules.staff.presentation.api.v1.schemas import (
    CurrentUserSchema,
    PermissionSchema,
)

access_router = APIRouter(prefix="/api/staff", tags=["Доступ"])


@access_router.get(
    "/me",
    response_model=CurrentUserSchema,
    description="Текущий пользователь и его права",
)
async def get_current_user(request: Request) -> CurrentUserSchema:
    async with container(context={Request: request}) as context:
        interactor = await context.get(GetCurrentUserInteractor)
        view = await interactor()

    return CurrentUserSchema.from_dto(view)


@access_router.get(
    "/permissions",
    response_model=list[PermissionSchema],
    description="Справочник прав",
)
async def list_permissions(request: Request) -> list[PermissionSchema]:
    async with container(context={Request: request}) as context:
        interactor = await context.get(ListPermissionsInteractor)
        items = await interactor()

    return [PermissionSchema.from_dto(item) for item in items]
