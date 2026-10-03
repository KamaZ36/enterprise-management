from uuid import UUID

from sqlalchemy import literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.infrastructure.readers.access_reader.base import (
    AccessReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import (
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
    USER_ROLES_TABLE,
)


class SQLAlchemyAccessReader(AccessReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_permission(
        self, user_id: UUID, permission_code: str, location_id: UUID | None
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
                    ROLE_PERMISSIONS_TABLE.c.permission_code == permission_code,
                ),
            )
            .limit(1)
        )
        return (await self._session.execute(query)).first() is not None
