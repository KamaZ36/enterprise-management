from uuid import UUID

from sqlalchemy import RowMapping, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_GRANT_RULES_TABLE,
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
)


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        await self._session.execute(
            insert(ROLES_TABLE).values(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description,
                level=role.level,
                is_system=role.is_system,
                is_assignable=role.is_assignable,
                is_wildcard=role.is_wildcard,
                created_at=role.created_at,
                updated_at=role.updated_at,
            )
        )

        await self._insert_permissions(role)
        await self._insert_grant_rules(role)

    async def save(self, role: Role) -> None:
        await self._session.execute(
            update(ROLES_TABLE)
            .where(ROLES_TABLE.c.id == role.id)
            .values(
                name=role.name,
                description=role.description,
                level=role.level,
                is_system=role.is_system,
                is_assignable=role.is_assignable,
                is_wildcard=role.is_wildcard,
                updated_at=role.updated_at,
            )
        )

        await self._session.execute(
            delete(ROLE_PERMISSIONS_TABLE).where(
                ROLE_PERMISSIONS_TABLE.c.role_id == role.id
            )
        )
        await self._session.execute(
            delete(ROLE_GRANT_RULES_TABLE).where(
                ROLE_GRANT_RULES_TABLE.c.granter_role_id == role.id
            )
        )

        await self._insert_permissions(role)
        await self._insert_grant_rules(role)

    async def get_by_id(self, role_id: UUID) -> Role | None:
        stmt = self._base_select().where(ROLES_TABLE.c.id == role_id)

        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_code(self, code: str) -> Role | None:
        stmt = self._base_select().where(ROLES_TABLE.c.code == code)

        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_many(self, role_ids: set[UUID]) -> dict[UUID, Role]:
        if not role_ids:
            return {}

        stmt = self._base_select().where(ROLES_TABLE.c.id.in_(role_ids))

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        return {row["id"]: self._to_entity(row) for row in rows}

    async def list(self) -> list[Role]:
        stmt = self._base_select().order_by(
            ROLES_TABLE.c.level.desc(),
            ROLES_TABLE.c.name.asc(),
        )

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        return [self._to_entity(row) for row in rows]

    def _base_select(self):
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

        return select(
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
        )

    async def _insert_permissions(self, role: Role) -> None:
        if not role.permission_codes:
            return

        await self._session.execute(
            insert(ROLE_PERMISSIONS_TABLE).values(
                [
                    {"role_id": role.id, "permission_code": code}
                    for code in role.permission_codes
                ]
            )
        )

    async def _insert_grant_rules(self, role: Role) -> None:
        if not role.grantable_role_ids:
            return

        await self._session.execute(
            insert(ROLE_GRANT_RULES_TABLE).values(
                [
                    {"granter_role_id": role.id, "grantable_role_id": grantable_id}
                    for grantable_id in role.grantable_role_ids
                ]
            )
        )

    def _to_entity(self, row: RowMapping) -> Role:
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
