from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
    SpecLineRole,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.tables import (
    TECH_CARD_LINES_TABLE,
    TECH_CARDS_TABLE,
)


class SQLAlchemyTechCardRepository(TechCardRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tech_card: TechCard) -> None:
        await self._session.execute(
            insert(TECH_CARDS_TABLE).values(**self._card_values(tech_card))
        )

        if tech_card.lines:
            await self._session.execute(
                insert(TECH_CARD_LINES_TABLE).values(
                    [
                        self._line_values(tech_card.id, line)
                        for line in tech_card.lines
                    ]
                )
            )

    async def get_by_id(self, tech_card_id: UUID) -> TechCard | None:
        row = (
            (
                await self._session.execute(
                    select(TECH_CARDS_TABLE).where(
                        TECH_CARDS_TABLE.c.id == tech_card_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        lines = (
            (
                await self._session.execute(
                    select(TECH_CARD_LINES_TABLE)
                    .where(TECH_CARD_LINES_TABLE.c.tech_card_id == tech_card_id)
                    .order_by(TECH_CARD_LINES_TABLE.c.id.asc())
                )
            )
            .mappings()
            .all()
        )

        return self._to_entity(row, lines)

    async def next_version(self, code: str) -> int:
        current = await self._session.scalar(
            select(func.max(TECH_CARDS_TABLE.c.version)).where(
                TECH_CARDS_TABLE.c.code == code
            )
        )

        return int(current or 0) + 1

    def _card_values(self, tech_card: TechCard) -> dict[str, object]:
        return {
            "id": tech_card.id,
            "code": tech_card.code,
            "version": tech_card.version,
            "name": tech_card.name,
            "basis": tech_card.basis.value,
            "valid_from": tech_card.valid_from,
            "comment": tech_card.comment,
            "created_by": tech_card.created_by,
            "created_at": tech_card.created_at,
        }

    def _line_values(self, tech_card_id: UUID, line: TechCardLine) -> dict[str, object]:
        return {
            "id": line.id,
            "tech_card_id": tech_card_id,
            "role": line.role.value,
            "nomenclature_id": line.nomenclature_id,
            "quantity": line.quantity,
            "loss_kind": line.loss_kind.value if line.loss_kind else None,
            "output_kind": line.output_kind.value if line.output_kind else None,
            "cost_coefficient": line.cost_coefficient,
        }

    def _to_entity(self, row, lines) -> TechCard:
        return TechCard(
            id=row["id"],
            code=row["code"],
            version=row["version"],
            name=row["name"],
            basis=TechCardBasis(row["basis"]),
            created_at=row["created_at"],
            lines=[
                TechCardLine(
                    id=line["id"],
                    role=SpecLineRole(line["role"]),
                    quantity=line["quantity"],
                    nomenclature_id=line["nomenclature_id"],
                    loss_kind=LossKind(line["loss_kind"])
                    if line["loss_kind"]
                    else None,
                    output_kind=OutputKind(line["output_kind"])
                    if line["output_kind"]
                    else None,
                    cost_coefficient=line["cost_coefficient"],
                )
                for line in lines
            ],
            created_by=row["created_by"],
            valid_from=row["valid_from"],
            comment=row["comment"],
        )
