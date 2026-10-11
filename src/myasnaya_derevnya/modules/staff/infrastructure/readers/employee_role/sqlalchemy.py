from uuid import UUID

from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.application.dto import EmployeeRoleListItem
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
)
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee_role.base import (
    EmployeeRoleReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_ASSIGNMENTS_TABLE,
    ROLES_TABLE,
)


class SQLAlchemyEmployeeRoleReader(EmployeeRoleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_for_user(self, user_id: UUID) -> list[EmployeeRoleListItem]:
        stmt = (
            select(
                ROLE_ASSIGNMENTS_TABLE.c.id,
                ROLE_ASSIGNMENTS_TABLE.c.role_id,
                ROLES_TABLE.c.code.label("role_code"),
                ROLES_TABLE.c.name.label("role_name"),
                ROLE_ASSIGNMENTS_TABLE.c.org_unit_id,
                ROLE_ASSIGNMENTS_TABLE.c.include_descendants,
                ROLE_ASSIGNMENTS_TABLE.c.status,
                ROLE_ASSIGNMENTS_TABLE.c.created_at.label("assigned_at"),
            )
            .join(ROLES_TABLE, ROLES_TABLE.c.id == ROLE_ASSIGNMENTS_TABLE.c.role_id)
            .where(
                ROLE_ASSIGNMENTS_TABLE.c.user_id == user_id,
                ROLE_ASSIGNMENTS_TABLE.c.status == RoleAssignmentStatus.ACTIVE.value,
            )
            .order_by(
                ROLES_TABLE.c.level.desc(),
                ROLE_ASSIGNMENTS_TABLE.c.created_at.desc(),
            )
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows]

    def _to_dto(self, row: RowMapping) -> EmployeeRoleListItem:
        return EmployeeRoleListItem(
            id=row["id"],
            role_id=row["role_id"],
            role_code=row["role_code"],
            role_name=row["role_name"],
            org_unit_id=row["org_unit_id"],
            include_descendants=row["include_descendants"],
            status=RoleAssignmentStatus(row["status"]),
            assigned_at=row["assigned_at"],
        )
