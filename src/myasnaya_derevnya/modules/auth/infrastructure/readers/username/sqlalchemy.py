from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.identity import UserIdentityType
from myasnaya_derevnya.modules.auth.infrastructure.readers.username.base import (
    UsernameReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import (
    USER_IDENTITIES_TABLE,
)


class SQLAlchemyUsernameReader(UsernameReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def usernames_for_users(
        self, user_ids: Collection[UUID]
    ) -> dict[UUID, str]:
        if not user_ids:
            return {}

        rows = (
            await self._session.execute(
                select(
                    USER_IDENTITIES_TABLE.c.user_id,
                    USER_IDENTITIES_TABLE.c.identifier,
                ).where(
                    USER_IDENTITIES_TABLE.c.user_id.in_(list(user_ids)),
                    USER_IDENTITIES_TABLE.c.identity_type
                    == UserIdentityType.USERNAME.value,
                )
            )
        ).all()

        return {row.user_id: row.identifier for row in rows}
