from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USER_CREDENTIALS_TABLE


class SQLAlchemyCredentialRepository(CredentialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user_credential: UserCredential) -> None:
        stmt = insert(USER_CREDENTIALS_TABLE).values(
            id=user_credential.id,
            user_id=user_credential.user_id,
            credential_type=user_credential.credential_type.value,
            secret=user_credential.secret,
            created_at=user_credential.created_at,
        )
        await self._session.execute(stmt)

    async def get_by_user_id_and_type(
        self, user_id: UUID, credential_type: UserCredentialType
    ) -> UserCredential | None:
        stmt = select(USER_CREDENTIALS_TABLE).where(
            USER_CREDENTIALS_TABLE.c.user_id == user_id,
            USER_CREDENTIALS_TABLE.c.credential_type == credential_type.value,
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def save(self, user_credential: UserCredential) -> None:
        stmt = (
            update(USER_CREDENTIALS_TABLE)
            .where(USER_CREDENTIALS_TABLE.c.id == user_credential.id)
            .values(secret=user_credential.secret)
        )
        await self._session.execute(stmt)

    def _to_entity(self, row: RowMapping) -> UserCredential:
        return UserCredential(
            id=row["id"],
            user_id=row["user_id"],
            credential_type=UserCredentialType(row["credential_type"]),
            secret=row["secret"],
            created_at=row["created_at"],
        )
