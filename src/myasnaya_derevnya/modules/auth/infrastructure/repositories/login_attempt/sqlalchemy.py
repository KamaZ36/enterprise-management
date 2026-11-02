from datetime import datetime

from sqlalchemy import RowMapping, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.login_attempt import LoginAttempt
from myasnaya_derevnya.modules.auth.infrastructure.repositories.login_attempt.base import (
    LoginAttemptRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import LOGIN_ATTEMPTS_TABLE


class SQLAlchemyLoginAttemptRepository(LoginAttemptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_identifier(self, identifier: str) -> LoginAttempt | None:
        result = await self._session.execute(
            select(LOGIN_ATTEMPTS_TABLE).where(
                LOGIN_ATTEMPTS_TABLE.c.identifier == identifier
            )
        )
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def save(self, attempt: LoginAttempt) -> None:
        stmt = insert(LOGIN_ATTEMPTS_TABLE).values(
            identifier=attempt.identifier,
            failed_attempts=attempt.failed_attempts,
            window_started_at=attempt.window_started_at,
            locked_until=attempt.locked_until,
            updated_at=attempt.updated_at,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[LOGIN_ATTEMPTS_TABLE.c.identifier],
            set_={
                "failed_attempts": stmt.excluded.failed_attempts,
                "window_started_at": stmt.excluded.window_started_at,
                "locked_until": stmt.excluded.locked_until,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._session.execute(stmt)

    async def delete_by_identifier(self, identifier: str) -> None:
        await self._session.execute(
            delete(LOGIN_ATTEMPTS_TABLE).where(
                LOGIN_ATTEMPTS_TABLE.c.identifier == identifier
            )
        )

    async def delete_stale(self, older_than: datetime) -> int:
        result = await self._session.execute(
            delete(LOGIN_ATTEMPTS_TABLE).where(
                LOGIN_ATTEMPTS_TABLE.c.updated_at < older_than
            )
        )

        return result.rowcount or 0

    def _to_entity(self, row: RowMapping) -> LoginAttempt:
        return LoginAttempt(
            identifier=row["identifier"],
            failed_attempts=row["failed_attempts"],
            window_started_at=row["window_started_at"],
            locked_until=row["locked_until"],
            updated_at=row["updated_at"],
        )
