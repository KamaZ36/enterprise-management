from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.organization.domain.entities.location import (
    Location,
    LocationType,
)
from myasnaya_derevnya.modules.organization.infrastructure.location.base import (
    LocationRepository,
)
from myasnaya_derevnya.modules.organization.infrastructure.tables import LOCATIONS_TABLE


class SQLAlchemyLocationRepository(LocationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, location: Location) -> None:
        stmt = insert(LOCATIONS_TABLE).values(
            id=location.id,
            location_type=location.location_type.value,
            name=location.name,
            code=location.code,
            address=location.address,
            is_active=location.is_active,
            created_at=location.created_at,
        )
        await self._session.execute(stmt)

    async def get_by_id(self, location_id: UUID) -> Location | None:
        stmt = select(LOCATIONS_TABLE).where(LOCATIONS_TABLE.c.id == location_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def save(self, location: Location) -> None:
        stmt = update(LOCATIONS_TABLE).values(
            id=location.id,
            location_type=location.location_type.value,
            name=location.name,
            code=location.code,
            address=location.address,
            is_active=location.is_active,
            created_at=location.created_at,
        )
        await self._session.execute(stmt)

    def _to_entity(self, row: RowMapping) -> Location:
        return Location(
            id=row["id"],
            location_type=LocationType(row["location_type"]),
            name=row["name"],
            code=row["code"],
            address=row["address"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )
