from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import (
    CurrentUserRole,
    CurrentUserScope,
    CurrentUserView,
)
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


class GetCurrentUserInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        role_assignment_repository: RoleAssignmentRepository,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._role_assignment_repository = role_assignment_repository
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(self) -> CurrentUserView:
        user_id = await self._identity_provider.get_current_user_id()

        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id
        )
        employee = await self._employee_repository.get_by_user_id(user_id)
        access = await self._access_service.access_map(user_id)


        scopes: tuple[CurrentUserScope, ...] = ()
        if access.by_unit:
            titles = await self._business_api.org_unit_titles(access.by_unit)
            scopes = tuple(
                CurrentUserScope(
                    id=unit_id,
                    title=titles.get(unit_id, str(unit_id)),
                    permissions=access.by_unit[unit_id],
                )
                for unit_id in sorted(access.by_unit, key=str)
            )

        return CurrentUserView(
            user_id=user_id,
            employee_id=employee.id if employee else None,
            first_name=employee.first_name if employee else None,
            last_name=employee.last_name if employee else None,
            middle_name=employee.middle_name if employee else None,
            position=employee.position if employee else None,
            roles=[
                CurrentUserRole(
                    code=item.role.code,
                    name=item.role.name,
                    org_unit_id=item.assignment.org_unit_id,
                )
                for item in assignments
            ],
            permissions=access.permissions,
            scopes=scopes,
        )
