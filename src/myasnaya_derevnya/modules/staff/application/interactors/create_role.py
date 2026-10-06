from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)


@dataclass(frozen=True, slots=True)
class CreateEmployeeRoleCommand:
    name: str
    code: str
    level: int
    description: str | None
    is_system: bool
    is_assignable: bool
    permissions: frozenset[str]


class CreateEmployeeRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_repository: RoleRepository,
        access_service: AccessService,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_repository = role_repository
        self._access_service = access_service
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateEmployeeRoleCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        await self._access_service.can(
            user_id=current_user_id, permission=MANAGE_ROLES, org_unit_id=None
        )

        role = Role.create(
            code=command.code,
            name=command.name,
            level=command.level,
            description=command.description,
            is_system=command.is_system,
            is_assignable=command.is_assignable,
        )

        await self._role_repository.add(role)
        await self._transaction_manager.commit()

        return role.id
