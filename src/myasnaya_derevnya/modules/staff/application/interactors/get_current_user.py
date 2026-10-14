from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.permissions import all_permissions
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import (
    CurrentUserRole,
    CurrentUserScope,
    CurrentUserView,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


class GetCurrentUserInteractor:
    """Кто вошёл и что ему доступно."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        role_assignment_repository: RoleAssignmentRepository,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._role_assignment_repository = role_assignment_repository
        self._business_api = business_api

    async def __call__(self) -> CurrentUserView:
        user_id = await self._identity_provider.get_current_user_id()

        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id
        )
        employee = await self._employee_repository.get_by_user_id(user_id)

        # Точки, где сотрудник вообще может работать: нужны переключателю контекста.
        scope_ids = {
            item.assignment.org_unit_id
            for item in assignments
            if item.assignment.org_unit_id is not None
        }
        titles = await self._business_api.org_unit_titles(scope_ids)

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
            permissions=_effective_permissions(assignments),
            scopes=tuple(
                CurrentUserScope(id=scope_id, title=titles.get(scope_id, str(scope_id)))
                for scope_id in sorted(scope_ids, key=str)
            ),
        )


def _effective_permissions(
    assignments: list[ResolvedAssignment],
) -> frozenset[str]:
    if any(item.role.is_wildcard for item in assignments):
        return frozenset(permission.code for permission in all_permissions())

    return frozenset(
        code for item in assignments for code in item.role.permission_codes
    )
