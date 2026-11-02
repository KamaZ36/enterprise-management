import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError, ValidationError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)

NAME_FIELDS = ("first_name", "last_name", "middle_name")


@dataclass(frozen=True, slots=True)
class UpdateEmployeeCommand:
    employee_id: UUID
    provided: frozenset[str]
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    phone_number: str | None = None
    position: str | None = None
    is_active: bool | None = None
    org_unit_id: UUID | None = None


class UpdateEmployeeInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        access_service: AccessService,
        business_api: BusinessAPI,
        role_assignment_repository: RoleAssignmentRepository,
        auth_api: AuthAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._access_service = access_service
        self._business_api = business_api
        self._role_assignment_repository = role_assignment_repository
        self._auth_api = auth_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateEmployeeCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        employee = await self._employee_repository.get_by_id(command.employee_id)
        if employee is None:
            raise EmployeeNotFound()

        target_org_unit_id = employee.org_unit_id
        if "org_unit_id" in command.provided and command.org_unit_id is not None:
            target_org_unit_id = command.org_unit_id

        for org_unit_id in {employee.org_unit_id, target_org_unit_id}:
            allowed = await self._access_service.can(
                user_id=current_user_id,
                permission=MANAGE_EMPLOYEES,
                org_unit_id=org_unit_id,
            )
            if not allowed:
                raise ForbiddenError()

        if target_org_unit_id != employee.org_unit_id:
            if not await self._business_api.org_unit_exists(target_org_unit_id):
                raise ValidationError()
            employee.transfer_to(target_org_unit_id)

        if any(field in command.provided for field in NAME_FIELDS):
            employee.rename(
                first_name=command.first_name or employee.first_name,
                last_name=command.last_name or employee.last_name,
                middle_name=(
                    command.middle_name
                    if "middle_name" in command.provided
                    else employee.middle_name
                ),
            )

        if "position" in command.provided and command.position:
            employee.change_position(command.position)

        if "phone_number" in command.provided:
            employee.change_phone(
                PhoneNumber.parse(command.phone_number)
                if command.phone_number
                else None
            )

        was_active = employee.is_active
        access_granted = False
        access_revoked = False
        revoked_roles = 0

        if command.is_active is not None:
            if command.is_active:
                employee.restore()
                if not was_active:
                    await self._auth_api.set_user_active(employee.user_id, True)
                    access_granted = True
            else:
                employee.dismiss(get_datetime_utc())
                if was_active:
                    revoked_roles = (
                        await self._role_assignment_repository.revoke_all_for_user(
                            employee.user_id
                        )
                    )
                    await self._auth_api.set_user_active(employee.user_id, False)
                    access_revoked = True

        await self._employee_repository.save(employee)
        await self._transaction_manager.commit()

        if access_granted:
            logger.info(
                "Сотрудник восстановлен: вход в систему разрешён",
                extra={
                    "employee_id": str(employee.id),
                    "target_user_id": str(employee.user_id),
                },
            )
        elif access_revoked:
            logger.info(
                "Сотрудник уволен: доступ отозван",
                extra={
                    "employee_id": str(employee.id),
                    "target_user_id": str(employee.user_id),
                    "revoked_roles": revoked_roles,
                },
            )

        logger.info(
            "Изменён сотрудник",
            extra={
                "employee_id": str(employee.id),
                "changed_fields": sorted(command.provided),
            },
        )
