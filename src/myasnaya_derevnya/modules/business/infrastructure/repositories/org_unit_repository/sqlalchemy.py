from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
from myasnaya_derevnya.modules.business.infrastructure.tables import (
    ORG_UNIT_CLOSURE_TABLE,
    ORG_UNITS_TABLE,
)


class SQLAlchemyOrgUnitRepository(OrgUnitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, org_unit: OrgUnit) -> None:
        await self._session.execute(
            insert(ORG_UNITS_TABLE).values(
                id=org_unit.id,
                parent_id=org_unit.parent_id,
                type=org_unit.type.value,
                code=org_unit.code,
                name=org_unit.name,
                address=org_unit.address,
                phone_number=(
                    org_unit.phone_number.value if org_unit.phone_number else None
                ),
                timezone=org_unit.timezone,
                is_active=org_unit.is_active,
                attributes=org_unit.attributes,
                created_at=org_unit.created_at,
                updated_at=org_unit.updated_at,
            )
        )

        await self._insert_closure(org_unit)

    async def save(self, org_unit: OrgUnit) -> None:
        await self._session.execute(
            update(ORG_UNITS_TABLE)
            .where(ORG_UNITS_TABLE.c.id == org_unit.id)
            .values(
                name=org_unit.name,
                address=org_unit.address,
                phone_number=(
                    org_unit.phone_number.value if org_unit.phone_number else None
                ),
                timezone=org_unit.timezone,
                is_active=org_unit.is_active,
                attributes=org_unit.attributes,
                updated_at=org_unit.updated_at,
            )
        )

    async def get_by_id(self, org_unit_id: UUID) -> OrgUnit | None:
        stmt = select(ORG_UNITS_TABLE).where(ORG_UNITS_TABLE.c.id == org_unit_id)
        result = await self._session.execute(stmt)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_children(self, org_unit_id: UUID) -> list[OrgUnit]:
        stmt = (
            select(ORG_UNITS_TABLE)
            .where(ORG_UNITS_TABLE.c.parent_id == org_unit_id)
            .order_by(ORG_UNITS_TABLE.c.name.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        return [self._to_entity(row) for row in rows]

    async def ancestors_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        stmt = select(ORG_UNIT_CLOSURE_TABLE.c.ancestor_id).where(
            ORG_UNIT_CLOSURE_TABLE.c.descendant_id == org_unit_id
        )
        result = await self._session.execute(stmt)

        return frozenset(row[0] for row in result)

    async def descendants_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        stmt = select(ORG_UNIT_CLOSURE_TABLE.c.descendant_id).where(
            ORG_UNIT_CLOSURE_TABLE.c.ancestor_id == org_unit_id
        )
        result = await self._session.execute(stmt)

        return frozenset(row[0] for row in result)

    async def _insert_closure(self, org_unit: OrgUnit) -> None:
        entries: list[dict] = [
            {
                "ancestor_id": org_unit.id,
                "descendant_id": org_unit.id,
                "depth": 0,
            }
        ]

        if org_unit.parent_id is not None:
            stmt = select(
                ORG_UNIT_CLOSURE_TABLE.c.ancestor_id,
                ORG_UNIT_CLOSURE_TABLE.c.depth,
            ).where(ORG_UNIT_CLOSURE_TABLE.c.descendant_id == org_unit.parent_id)

            result = await self._session.execute(stmt)

            entries.extend(
                {
                    "ancestor_id": row[0],
                    "descendant_id": org_unit.id,
                    "depth": row[1] + 1,
                }
                for row in result
            )

        await self._session.execute(insert(ORG_UNIT_CLOSURE_TABLE).values(entries))

    async def root_of(self, org_unit_id: UUID) -> UUID | None:
        stmt = (
            select(ORG_UNIT_CLOSURE_TABLE.c.ancestor_id)
            .where(ORG_UNIT_CLOSURE_TABLE.c.descendant_id == org_unit_id)
            .order_by(ORG_UNIT_CLOSURE_TABLE.c.depth.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_root_id(self) -> UUID:
        stmt = select(ORG_UNITS_TABLE.c.id).where(ORG_UNITS_TABLE.c.parent_id.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    def _to_entity(self, row: RowMapping) -> OrgUnit:
        return OrgUnit(
            id=row["id"],
            parent_id=row["parent_id"],
            type=OrgUnitType(row["type"]),
            code=row["code"],
            name=row["name"],
            address=row["address"],
            phone_number=(
                PhoneNumber.parse(row["phone_number"])
                if row["phone_number"] is not None
                else None
            ),
            timezone=row["timezone"],
            is_active=row["is_active"],
            attributes=row["attributes"] or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
