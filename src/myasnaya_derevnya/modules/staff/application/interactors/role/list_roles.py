from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import RoleListItem
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.permissions import READ_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.readers.role.base import RoleReader


class ListRolesInteractor:
    """Справочник ролей: без него нельзя назначить роль сотруднику."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_reader: RoleReader,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_reader = role_reader
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(self) -> list[RoleListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=READ_ROLES,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        return await self._role_reader.list()
