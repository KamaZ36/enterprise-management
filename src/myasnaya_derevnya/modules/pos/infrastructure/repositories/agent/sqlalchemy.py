from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.domain.entities.agent import (
    PosAgent,
    PosAgentStatus,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import POS_AGENTS_TABLE


class SQLAlchemyPosAgentRepository(PosAgentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, agent: PosAgent) -> None:
        await self._session.execute(
            insert(POS_AGENTS_TABLE).values(
                id=agent.id,
                source_id=agent.source_id,
                install_id=agent.install_id,
                api_key_hash=agent.api_key_hash,
                api_key_prefix=agent.api_key_prefix,
                hostname=agent.hostname,
                version=agent.version,
                status=agent.status.value,
                pending_receipts=agent.pending_receipts,
                last_seen_at=agent.last_seen_at,
                last_success_at=agent.last_success_at,
                last_error=agent.last_error,
                is_active=agent.is_active,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
            )
        )

    async def save(self, agent: PosAgent) -> None:
        await self._session.execute(
            update(POS_AGENTS_TABLE)
            .where(POS_AGENTS_TABLE.c.id == agent.id)
            .values(
                install_id=agent.install_id,
                api_key_hash=agent.api_key_hash,
                api_key_prefix=agent.api_key_prefix,
                hostname=agent.hostname,
                version=agent.version,
                status=agent.status.value,
                pending_receipts=agent.pending_receipts,
                last_seen_at=agent.last_seen_at,
                last_success_at=agent.last_success_at,
                last_error=agent.last_error,
                is_active=agent.is_active,
                updated_at=agent.updated_at,
            )
        )

    async def get_by_id(self, agent_id: UUID) -> PosAgent | None:
        row = (
            (
                await self._session.execute(
                    select(POS_AGENTS_TABLE).where(POS_AGENTS_TABLE.c.id == agent_id)
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def get_by_key_hash(self, api_key_hash: str) -> PosAgent | None:
        row = (
            (
                await self._session.execute(
                    select(POS_AGENTS_TABLE).where(
                        POS_AGENTS_TABLE.c.api_key_hash == api_key_hash
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def list_by_source(self, source_id: UUID) -> list[PosAgent]:
        rows = (
            (
                await self._session.execute(
                    select(POS_AGENTS_TABLE)
                    .where(POS_AGENTS_TABLE.c.source_id == source_id)
                    .order_by(POS_AGENTS_TABLE.c.created_at.asc())
                )
            )
            .mappings()
            .all()
        )

        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row) -> PosAgent:
        return PosAgent(
            id=row["id"],
            source_id=row["source_id"],
            install_id=row["install_id"],
            api_key_hash=row["api_key_hash"],
            api_key_prefix=row["api_key_prefix"],
            hostname=row["hostname"],
            version=row["version"],
            status=PosAgentStatus(row["status"]),
            pending_receipts=row["pending_receipts"],
            last_seen_at=row["last_seen_at"],
            last_success_at=row["last_success_at"],
            last_error=row["last_error"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
