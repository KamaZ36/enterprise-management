from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_READ
from myasnaya_derevnya.modules.business.infrastructure.readers.org_unit.base import (
    OrgUnitReader,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class ListOrgUnitsInteractor:
    """Оргструктура для интерфейса: нужна для выбора склада и разрезов отчётов."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        org_unit_reader: OrgUnitReader,
        org_unit_repository: OrgUnitRepository,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._org_unit_reader = org_unit_reader
        self._org_unit_repository = org_unit_repository
        self._staff_api = staff_api

    async def __call__(self) -> list[OrgUnitListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        root_org_unit_id = await self._org_unit_repository.get_root_id()
        if root_org_unit_id is None:
            # Структуры ещё нет — показывать нечего и нечего защищать.
            return []

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=ORG_UNIT_READ,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        return await self._org_unit_reader.list()
