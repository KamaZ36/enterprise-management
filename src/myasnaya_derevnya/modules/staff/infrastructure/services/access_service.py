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
        self, user_id: UUID, permission: Permission, location_id: UUID | None
    ) -> bool:
        result = await self._query(
            user_id=user_id, permission=permission, location_id=location_id
        )
        return result

    async def require(
        self, user_id: UUID, permission: Permission, location_id: UUID
    ) -> None:
        result = await self._query(
            user_id=user_id, permission=permission, location_id=location_id
        )
        if not result:
            raise ForbiddenError()

    async def _query(
        self, user_id: UUID, permission: Permission, location_id: UUID | None
    ) -> bool:
        query = (
            select(literal(1))
            .select_from(
                USER_ROLES_TABLE.join(
                    ROLES_TABLE, ROLES_TABLE.c.id == USER_ROLES_TABLE.c.role_id
                ).outerjoin(
                    ROLE_PERMISSIONS_TABLE,
                    ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id,
                )
            )
            .where(
                USER_ROLES_TABLE.c.user_id == user_id,
                or_(
                    USER_ROLES_TABLE.c.location_id.is_(None),
                    USER_ROLES_TABLE.c.location_id == location_id,
                ),
                or_(
                    ROLES_TABLE.c.grants_all.is_(True),
                    ROLE_PERMISSIONS_TABLE.c.permission_code == permission.code,
                ),
            )
            .limit(1)
        )
        return (await self._session.execute(query)).first() is not None
