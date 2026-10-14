from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    EmptyTechCardError,
    InvalidTechCardLineError,
    MainOutputRequiredError,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)


def test_disassembly_card_keeps_components_outputs_and_losses() -> None:
    card = TechCard.create(
        code="BEEF-SHOULDER",
        name="Разделка говяжьей лопатки",
        basis=TechCardBasis.INPUT,
        lines=[
            TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(100)),
            TechCardLine.output(
                nomenclature_id=uuid4(),
                quantity=Decimal(30),
                output_kind=OutputKind.MAIN,
            ),
            TechCardLine.output(
                nomenclature_id=uuid4(),
                quantity=Decimal(25),
                output_kind=OutputKind.BY_PRODUCT,
                cost_coefficient=Decimal("0.5"),
            ),
            TechCardLine.loss(loss_kind=LossKind.TRIMMING, quantity=Decimal(10)),
        ],
    )

    assert card.version == 1
    assert len(card.components) == 1
    assert len(card.outputs) == 2
    assert len(card.losses) == 1
    assert card.main_output is not None
    assert card.main_output.quantity == Decimal(30)


def test_card_without_outputs_is_rejected() -> None:
    with pytest.raises(EmptyTechCardError):
        TechCard.create(
            code="EMPTY",
            name="Пустая",
            basis=TechCardBasis.INPUT,
            lines=[
                TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(1))
            ],
        )


def test_output_based_card_needs_exactly_one_main_output() -> None:
    with pytest.raises(MainOutputRequiredError):
        TechCard.create(
            code="SAUSAGE",
            name="Колбаса",
            basis=TechCardBasis.OUTPUT,
            lines=[
                TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(80)),
                TechCardLine.output(
                    nomenclature_id=uuid4(),
                    quantity=Decimal(50),
                    output_kind=OutputKind.BY_PRODUCT,
                ),
                TechCardLine.output(
                    nomenclature_id=uuid4(),
                    quantity=Decimal(50),
                    output_kind=OutputKind.BY_PRODUCT,
                ),
            ],
        )


def test_zero_quantity_is_rejected() -> None:
    with pytest.raises(InvalidTechCardLineError):
        TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(0))


def test_non_positive_coefficient_is_rejected() -> None:
    with pytest.raises(InvalidTechCardLineError):
        TechCardLine.output(
            nomenclature_id=uuid4(),
            quantity=Decimal(10),
            cost_coefficient=Decimal(0),
        )


def test_blank_code_is_rejected() -> None:
    with pytest.raises(InvalidTechCardLineError):
        TechCard.create(
            code="   ",
            name="Без кода",
            basis=TechCardBasis.INPUT,
            lines=[
                TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(1)),
                TechCardLine.output(nomenclature_id=uuid4(), quantity=Decimal(1)),
            ],
        )
