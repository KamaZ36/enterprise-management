from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialProviderType,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import USER_CREDENTIALS_TABLE


class SQLAlchemyCredentialRepository(CredentialRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, credential: UserCredential) -> None:
        stmt = insert(USER_CREDENTIALS_TABLE).values(
            id=credential.id,
            user_id=credential.user_id,
            provider=credential.provider.value,
            identifier=credential.identifier,
            password_hash=credential.password_hash,
        )
        await self._session.execute(stmt)

    async def save(self, credential: UserCredential) -> None:
        stmt = update(USER_CREDENTIALS_TABLE).values(
            identifier=credential.identifier,
            password_hash=credential.password_hash,
        )
        await self._session.execute(stmt)

    async def get_by_identifier(self, identifier: str) -> UserCredential | None:
        stmt = select(USER_CREDENTIALS_TABLE).where(
            USER_CREDENTIALS_TABLE.c.identifier == identifier
        )
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            raise NotImplementedError

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> UserCredential:
        return UserCredential(
            id=row["id"],
            user_id=row["user_id"],
            provider=UserCredentialProviderType(row["provider"]),
            identifier=row["identifier"],
            password_hash=row["password_hash"],
        )
