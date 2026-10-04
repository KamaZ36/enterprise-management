from uuid import UUID

from sqlalchemy import literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.staff.infrastructure.tables import (
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
    USER_ROLES_TABLE,
)


class SQLAlchemyAccessService(AccessService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_permission(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> bool:
        result = await self._query(
            user_id=user_id, permission=permission, location_id=location_id
        )
        return result

    async def require(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> None:
        result = await self._query(
            user_id=user_id, permission=permission, location_id=location_id
        )
        if not result:
            raise ForbiddenError()

    async def _query(
        self,
        user_id: UUID,
        permission: Permission,
        location_id: UUID | None,
    ) -> bool:
        where_clauses = [
            USER_ROLES_TABLE.c.user_id == user_id,
            or_(
                ROLES_TABLE.c.grants_all.is_(True),
                ROLE_PERMISSIONS_TABLE.c.permission_code == permission.code,
            ),
        ]

        if location_id is not None:
            where_clauses.append(
                or_(
                    USER_ROLES_TABLE.c.location_id == location_id,
                    USER_ROLES_TABLE.c.location_id.is_(None),
                )
            )
        else:
            where_clauses.append(USER_ROLES_TABLE.c.location_id.is_(None))

        query = (
            select(literal(1))
            .select_from(
                USER_ROLES_TABLE.join(
                    ROLES_TABLE,
                    ROLES_TABLE.c.id == USER_ROLES_TABLE.c.role_id,
                ).outerjoin(
                    ROLE_PERMISSIONS_TABLE,
                    ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id,
                )
            )
            .where(*where_clauses)
            .limit(1)
        )

        return (await self._session.execute(query)).first() is not None
