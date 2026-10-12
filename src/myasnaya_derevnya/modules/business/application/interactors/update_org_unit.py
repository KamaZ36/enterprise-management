from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.business.application.errors import OrgUnitNotFound
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_UPDATE
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class UpdateOrgUnitCommand:
    org_unit_id: UUID
    provided: frozenset[str]
    name: str | None = None
    address: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None


class UpdateOrgUnitInteractor:
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

    async def __call__(self, command: UpdateOrgUnitCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._org_unit_repository.get_root_id()

        if not await self._staff_api.can(
            user_id=current_user_id,
            permission=ORG_UNIT_UPDATE,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        org_unit = await self._org_unit_repository.get_by_id(command.org_unit_id)
        if org_unit is None:
            raise OrgUnitNotFound(command.org_unit_id)

        if "name" in command.provided and command.name:
            org_unit.rename(command.name)

        if "address" in command.provided or "phone_number" in command.provided:
            phone_number = org_unit.phone_number
            if "phone_number" in command.provided:
                phone_number = (
                    PhoneNumber.parse(command.phone_number)
                    if command.phone_number
                    else None
                )

            org_unit.change_contacts(
                address=(
                    command.address
                    if "address" in command.provided
                    else org_unit.address
                ),
                phone_number=phone_number,
            )

        if command.is_active is not None:
            if command.is_active:
                org_unit.activate()
            else:
                org_unit.deactivate()

        await self._org_unit_repository.save(org_unit)
        await self._transaction_manager.commit()
