from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.application.services.permission_codes import (
    ensure_known_permissions,
)
from myasnaya_derevnya.modules.staff.domain.errors import (
    RoleIsSystemError,
    RoleNotFound,
)
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)


@dataclass(frozen=True, slots=True)
class UpdateRoleCommand:
    role_id: UUID
    provided: frozenset[str]
    name: str | None = None
    description: str | None = None
    level: int | None = None
    permission_codes: frozenset[str] | None = None


class UpdateRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_repository: RoleRepository,
        access_service: AccessService,
        business_api: BusinessAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_repository = role_repository
        self._access_service = access_service
        self._business_api = business_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateRoleCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=MANAGE_ROLES,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        role = await self._role_repository.get_by_id(command.role_id)
        if role is None:
            raise RoleNotFound(command.role_id)

        if role.is_system:
            raise RoleIsSystemError(role.code)

        if command.permission_codes is not None:
            ensure_known_permissions(command.permission_codes)

        if "name" in command.provided and command.name:
            role.rename(command.name)

        if "description" in command.provided:
            role.change_description(command.description)

        if "level" in command.provided and command.level is not None:
            role.change_level(command.level)

        if command.permission_codes is not None:
            role.change_permissions(command.permission_codes)

        await self._role_repository.save(role)
        await self._transaction_manager.commit()
