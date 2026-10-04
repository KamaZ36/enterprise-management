from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.location import (
    Location,
    LocationType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFound
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.location.base import (
    LocationRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import LOCATIONS_TABLE


class SQLAlchemyLocationRepository(LocationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, location: Location) -> None:
        stmt = insert(LOCATIONS_TABLE).values(
            id=location.id,
            name=location.name,
            location_type=location.location_type.value,
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
            raise LocationNotFound()

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> Location:
        return Location(
            id=row["id"],
            name=row["name"],
            location_type=LocationType(row["location_type"]),
            address=row["address"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )
