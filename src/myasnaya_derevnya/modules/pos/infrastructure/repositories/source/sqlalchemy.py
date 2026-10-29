from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import POS_SOURCES_TABLE


class SQLAlchemyPosSourceRepository(PosSourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, source: PosSource) -> None:
        await self._session.execute(
            insert(POS_SOURCES_TABLE).values(
                id=source.id,
                doka_org_id=source.doka_org_id,
                name=source.name,
                org_unit_id=source.org_unit_id,
                is_active=source.is_active,
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
        )

    async def save(self, source: PosSource) -> None:
        await self._session.execute(
            update(POS_SOURCES_TABLE)
            .where(POS_SOURCES_TABLE.c.id == source.id)
            .values(
                name=source.name,
                org_unit_id=source.org_unit_id,
                is_active=source.is_active,
                updated_at=source.updated_at,
            )
        )

    async def get_by_id(self, source_id: UUID) -> PosSource | None:
        row = (
            (
                await self._session.execute(
                    select(POS_SOURCES_TABLE).where(
                        POS_SOURCES_TABLE.c.id == source_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def get_by_doka_org_id(self, doka_org_id: str) -> PosSource | None:
        row = (
            (
                await self._session.execute(
                    select(POS_SOURCES_TABLE).where(
                        POS_SOURCES_TABLE.c.doka_org_id == doka_org_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        return self._to_entity(row) if row is not None else None

    async def list_all(self) -> list[PosSource]:
        rows = (
            (
                await self._session.execute(
                    select(POS_SOURCES_TABLE).order_by(
                        POS_SOURCES_TABLE.c.name.asc()
                    )
                )
            )
            .mappings()
            .all()
        )

        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row) -> PosSource:
        return PosSource(
            id=row["id"],
            doka_org_id=row["doka_org_id"],
            name=row["name"],
            org_unit_id=row["org_unit_id"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
