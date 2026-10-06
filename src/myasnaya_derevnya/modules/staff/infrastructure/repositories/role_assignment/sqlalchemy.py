from uuid import UUID

from sqlalchemy import RowMapping, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
    RoleAssignmentStatus,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_ASSIGNMENTS_TABLE,
    ROLE_GRANT_RULES_TABLE,
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
)


class SQLAlchemyRoleAssignmentRepository(RoleAssignmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, assignment: RoleAssignment) -> None:
        await self._session.execute(
            insert(ROLE_ASSIGNMENTS_TABLE).values(
                id=assignment.id,
                user_id=assignment.user_id,
                role_id=assignment.role_id,
                company_id=assignment.company_id,
                org_unit_id=assignment.org_unit_id,
                include_descendants=assignment.include_descendants,
                status=assignment.status.value,
                granted_by_user_id=assignment.granted_by_user_id,
                created_at=assignment.created_at,
            )
        )

    async def save(self, assignment: RoleAssignment) -> None:
        await self._session.execute(
            update(ROLE_ASSIGNMENTS_TABLE)
            .where(ROLE_ASSIGNMENTS_TABLE.c.id == assignment.id)
            .values(
                include_descendants=assignment.include_descendants,
                status=assignment.status.value,
            )
        )

    async def get_by_id(self, assignment_id: UUID) -> RoleAssignment | None:
        stmt = select(ROLE_ASSIGNMENTS_TABLE).where(
            ROLE_ASSIGNMENTS_TABLE.c.id == assignment_id
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_assignment(row)

    async def load_active_for_user(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> list[ResolvedAssignment]:
        stmt = select(ROLE_ASSIGNMENTS_TABLE).where(
            ROLE_ASSIGNMENTS_TABLE.c.user_id == user_id,
            ROLE_ASSIGNMENTS_TABLE.c.company_id == company_id,
            ROLE_ASSIGNMENTS_TABLE.c.status == RoleAssignmentStatus.ACTIVE.value,
        )

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        if not rows:
            return []

        assignments = [self._to_assignment(row) for row in rows]
        role_ids = {a.role_id for a in assignments}
        roles = await self._load_roles(role_ids)

        resolved: list[ResolvedAssignment] = []
        for assignment in assignments:
            role = roles.get(assignment.role_id)
            if role is None:
                continue
            resolved.append(ResolvedAssignment(assignment=assignment, role=role))

        return resolved

    async def _load_roles(self, role_ids: set[UUID]) -> dict[UUID, Role]:
        permissions_subq = (
            select(func.array_agg(ROLE_PERMISSIONS_TABLE.c.permission_code))
            .where(ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id)
            .correlate(ROLES_TABLE)
            .scalar_subquery()
        )

        grantable_subq = (
            select(func.array_agg(ROLE_GRANT_RULES_TABLE.c.grantable_role_id))
            .where(ROLE_GRANT_RULES_TABLE.c.granter_role_id == ROLES_TABLE.c.id)
            .correlate(ROLES_TABLE)
            .scalar_subquery()
        )

        stmt = select(
            ROLES_TABLE.c.id,
            ROLES_TABLE.c.code,
            ROLES_TABLE.c.name,
            ROLES_TABLE.c.description,
            ROLES_TABLE.c.level,
            ROLES_TABLE.c.is_system,
            ROLES_TABLE.c.is_assignable,
            ROLES_TABLE.c.is_wildcard,
            ROLES_TABLE.c.created_at,
            ROLES_TABLE.c.updated_at,
            permissions_subq.label("permission_codes"),
            grantable_subq.label("grantable_role_ids"),
        ).where(ROLES_TABLE.c.id.in_(role_ids))

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        return {row["id"]: self._to_role(row) for row in rows}

    def _to_assignment(self, row: RowMapping) -> RoleAssignment:
        return RoleAssignment(
            id_=row["id"],
            user_id=row["user_id"],
            role_id=row["role_id"],
            company_id=row["company_id"],
            org_unit_id=row["org_unit_id"],
            include_descendants=row["include_descendants"],
            status=RoleAssignmentStatus(row["status"]),
            granted_by_user_id=row["granted_by_user_id"],
            created_at=row["created_at"],
        )

    def _to_role(self, row: RowMapping) -> Role:
        return Role(
            id_=row["id"],
            code=row["code"],
            name=row["name"],
            description=row["description"],
            level=row["level"],
            is_system=row["is_system"],
            is_assignable=row["is_assignable"],
            is_wildcard=row["is_wildcard"],
            permission_codes=frozenset(row["permission_codes"] or ()),
            grantable_role_ids=frozenset(row["grantable_role_ids"] or ()),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
