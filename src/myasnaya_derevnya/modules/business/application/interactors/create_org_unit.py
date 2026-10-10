from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_CREATE
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateOrgUnitCommand:
    parent_id: UUID
    type: OrgUnitType
    code: str
    name: str
    address: str | None
    phone_number: str | None


class CreateOrgUnitInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        org_unit_repository: OrgUnitRepository,
        transaction_manager: TransactionManager,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._org_unit_repository = org_unit_repository
        self._transaction_manager = transaction_manager
        self._staff_api = staff_api

    async def __call__(self, command: CreateOrgUnitCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._org_unit_repository.get_root_id()

        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=ORG_UNIT_CREATE,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        phone_number = (
            PhoneNumber.parse(command.phone_number) if command.phone_number else None
        )

        org_unit = OrgUnit.create_child(
            parent_id=command.parent_id,
            type=command.type,
            code=command.code,
            name=command.name,
            address=command.address,
            phone_number=phone_number,
        )

        await self._org_unit_repository.add(org_unit)
        await self._transaction_manager.commit()

        return org_unit.id
