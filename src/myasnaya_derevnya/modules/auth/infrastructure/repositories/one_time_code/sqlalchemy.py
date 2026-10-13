from datetime import datetime

from sqlalchemy import RowMapping, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.one_time_code import OneTimeCode
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.base import (
    OneTimeCodeRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import ONE_TIME_CODES_TABLE


class SQLAlchemyOneTimeCodeRepository(OneTimeCodeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, code: OneTimeCode) -> None:
        stmt = insert(ONE_TIME_CODES_TABLE).values(
            id=code.id,
            identifier=code.identifier,
            code_hash=code.code_hash,
            expires_at=code.expires_at,
            attempts=code.attempts,
            max_attempts=code.max_attempts,
            created_at=code.created_at,
        )
        await self._session.execute(stmt)

    async def get_latest_by_identifier(self, identifier: str) -> OneTimeCode | None:
        query = (
            select(ONE_TIME_CODES_TABLE)
            .where(ONE_TIME_CODES_TABLE.c.identifier == identifier)
            .order_by(ONE_TIME_CODES_TABLE.c.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def update(self, code: OneTimeCode) -> None:
        stmt = (
            update(ONE_TIME_CODES_TABLE)
            .where(ONE_TIME_CODES_TABLE.c.id == code.id)
            .values(attempts=code.attempts)
        )
        await self._session.execute(stmt)

    async def delete_by_identifier(self, identifier: str) -> None:
        stmt = delete(ONE_TIME_CODES_TABLE).where(
            ONE_TIME_CODES_TABLE.c.identifier == identifier
        )
        await self._session.execute(stmt)

    async def count_created_since(self, identifier: str, since: datetime) -> int:
        query = (
            select(func.count())
            .select_from(ONE_TIME_CODES_TABLE)
            .where(
                ONE_TIME_CODES_TABLE.c.identifier == identifier,
                ONE_TIME_CODES_TABLE.c.created_at >= since,
            )
        )
        result = await self._session.execute(query)

        return result.scalar_one()

    def _to_entity(self, row: RowMapping) -> OneTimeCode:
        return OneTimeCode(
            id=row["id"],
            identifier=row["identifier"],
            code_hash=row["code_hash"],
            expires_at=row["expires_at"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            created_at=row["created_at"],
        )
