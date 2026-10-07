from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
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
class CreateRoleCommand:
    name: str
    code: str
    description: str | None
    level: int
    is_system: bool
    is_assignable: bool
    is_wildcard: bool
    permission_codes: frozenset[str]
    grantable_role_ids: frozenset[UUID]


class CreateRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_repository: RoleRepository,
        transaction_manager: TransactionManager,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_repository = role_repository
        self._transaction_manager = transaction_manager
        self._access_service = access_service

    async def __call__(self, command: CreateRoleCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        if not await self._access_service.can(
            user_id=current_user_id, permission=MANAGE_ROLES, org_unit_id=None
        ):
            raise ForbiddenError()

        role = Role.create(
            code=command.code,
            name=command.name,
            level=command.level,
            description=command.description,
            is_system=command.is_system,
            is_assignable=command.is_assignable,
            is_wildcard=command.is_wildcard,
            permission_codes=command.permission_codes,
            grantable_role_ids=command.grantable_role_ids,
        )

        await self._role_repository.add(role)
        await self._transaction_manager.commit()

        return role.id
