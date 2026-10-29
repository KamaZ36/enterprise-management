from datetime import date
from decimal import Decimal
from uuid import uuid4

from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.presentation.production_api import (
    ProductionAPI,
)

ON_DATE = date(2026, 10, 24)


class FakeTechCardRepository:
    def __init__(self, tech_card: TechCard | None) -> None:
        self.tech_card = tech_card

    async def get_effective_by_output_nomenclature(self, nomenclature_id, on_date):
        return self.tech_card


def build_card(
    *,
    basis: TechCardBasis,
    output_id,
    component_id,
    main_output_quantity: Decimal,
    component_quantity: Decimal,
) -> TechCard:
    return TechCard.create(
        code="PYTEST-CARD",
        name="Тестовая техкарта",
        basis=basis,
        lines=[
            TechCardLine.component(
                nomenclature_id=component_id, quantity=component_quantity
            ),
            TechCardLine.output(
                nomenclature_id=output_id,
                quantity=main_output_quantity,
            ),
            TechCardLine.loss(loss_kind=LossKind.SHRINKAGE, quantity=Decimal(1)),
        ],
    )


async def test_output_basis_recipe_is_scaled_to_one_unit() -> None:
    component_id = uuid4()
    output_id = uuid4()
    card = build_card(
        basis=TechCardBasis.OUTPUT,
        output_id=output_id,
        component_id=component_id,
        main_output_quantity=Decimal("0.5"),
        component_quantity=Decimal("0.1"),
    )
    api = ProductionAPI(tech_card_repository=FakeTechCardRepository(card))

    recipe = await api.recipe_for_output(output_id, ON_DATE)

    assert recipe is not None
    assert recipe.main_output_quantity == Decimal("0.5")
    assert len(recipe.components) == 1
    assert recipe.components[0].nomenclature_id == component_id
    assert recipe.components[0].quantity_per_output == Decimal("0.2")
    assert recipe.loss_line_count == 1


async def test_input_basis_card_is_not_exploded() -> None:
    component_id = uuid4()
    output_id = uuid4()
    card = build_card(
        basis=TechCardBasis.INPUT,
        output_id=output_id,
        component_id=component_id,
        main_output_quantity=Decimal(1),
        component_quantity=Decimal(2),
    )
    api = ProductionAPI(tech_card_repository=FakeTechCardRepository(card))

    assert await api.recipe_for_output(output_id, ON_DATE) is None


async def test_missing_tech_card_returns_none() -> None:
    api = ProductionAPI(tech_card_repository=FakeTechCardRepository(None))

    assert await api.recipe_for_output(uuid4(), ON_DATE) is None
