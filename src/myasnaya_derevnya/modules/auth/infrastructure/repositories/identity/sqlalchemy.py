from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.errors import UserIdentityNotFound
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USER_IDENTITIES_TABLE


class SQLAlchemyUserIdentityRepository(UserIdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_identity: UserIdentity) -> None:
        stmt = insert(USER_IDENTITIES_TABLE).values(
            id=user_identity.id,
            user_id=user_identity.user_id,
            identity_type=user_identity.identity_type.value,
            identifier=user_identity.identifier,
            created_at=user_identity.created_at,
        )
        await self._session.execute(stmt)

    async def get_by_identifier_and_type(
        self, identifier: str, identity_type: UserIdentityType
    ) -> UserIdentity | None:
        stmt = select(USER_IDENTITIES_TABLE).where(
            USER_IDENTITIES_TABLE.c.identifier == identifier,
            USER_IDENTITIES_TABLE.c.identity_type == identity_type.value,
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            raise UserIdentityNotFound()

        return self._to_entity(row)

    async def save(self, user_identity: UserIdentity) -> None:
        stmt = (
            update(USER_IDENTITIES_TABLE)
            .where(USER_IDENTITIES_TABLE.c.id == user_identity.id)
            .values(
                identifier=user_identity.identifier,
            )
        )
        await self._session.execute(stmt)

    def _to_entity(self, row: RowMapping) -> UserIdentity:
        return UserIdentity(
            id=row["id"],
            user_id=row["user_id"],
            identity_type=UserIdentityType(row["identity_type"]),
            identifier=row["identifier"],
            created_at=row["identifier"],
        )
