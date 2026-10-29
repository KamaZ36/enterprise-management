from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)


@dataclass(frozen=True, slots=True)
class RecipeComponent:
    nomenclature_id: UUID
    quantity_per_output: Decimal


@dataclass(frozen=True, slots=True)
class TechCardRecipe:
    """Развёртка техкарты на одну единицу главного выхода."""

    tech_card_id: UUID
    code: str
    version: int
    main_output_nomenclature_id: UUID
    main_output_quantity: Decimal
    components: tuple[RecipeComponent, ...]
    loss_line_count: int


class ProductionAPI:
    def __init__(self, tech_card_repository: TechCardRepository) -> None:
        self._tech_card_repository = tech_card_repository

    async def recipe_for_output(
        self, nomenclature_id: UUID, on_date: date
    ) -> TechCardRecipe | None:
        """Возвращает техкарту, если номенклатура является её главным выходом.

        Количество компонентов пересчитано на одну единицу главного выхода.
        Потери не имеют номенклатуры и не участвуют в списании: их стоимость
        уже растворена в себестоимости выхода.
        """

        tech_card = await self._tech_card_repository.get_effective_by_output_nomenclature(
            nomenclature_id, on_date
        )
        if tech_card is None or tech_card.basis is not TechCardBasis.OUTPUT:
            # Разборка (basis=input) не разворачивается: её выходы уже лежат
            # на складе отдельными позициями, и продажа списывает именно их.
            return None

        main_output = tech_card.main_output
        if main_output is None or main_output.quantity <= 0:
            return None

        components = tuple(
            RecipeComponent(
                nomenclature_id=line.nomenclature_id,
                quantity_per_output=line.quantity / main_output.quantity,
            )
            for line in tech_card.components
            if line.nomenclature_id is not None
        )

        if not components:
            return None

        return TechCardRecipe(
            tech_card_id=tech_card.id,
            code=tech_card.code,
            version=tech_card.version,
            main_output_nomenclature_id=nomenclature_id,
            main_output_quantity=main_output.quantity,
            components=components,
            loss_line_count=len(tech_card.losses),
        )
