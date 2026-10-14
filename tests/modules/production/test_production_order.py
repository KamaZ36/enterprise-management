from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    EmptyBatchError,
    EmptyProductionOutputError,
    OutputExceedsInputError,
    ProductionOrderLineNotFoundError,
    ProductionOrderNotDraftError,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.utils import get_datetime_utc


def make_card() -> TechCard:
    return TechCard.create(
        code="BEEF-SHOULDER",
        name="Разделка говяжьей лопатки",
        basis=TechCardBasis.INPUT,
        lines=[
            TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(100)),
            TechCardLine.output(
                nomenclature_id=uuid4(),
                quantity=Decimal(40),
                output_kind=OutputKind.MAIN,
            ),
            TechCardLine.output(
                nomenclature_id=uuid4(),
                quantity=Decimal(30),
                output_kind=OutputKind.BY_PRODUCT,
            ),
            TechCardLine.loss(loss_kind=LossKind.TRIMMING, quantity=Decimal(30)),
        ],
    )


def make_order(batch_count: str = "1") -> ProductionOrder:
    return ProductionOrder.create(
        warehouse_id=uuid4(),
        tech_card=make_card(),
        batch_count=Decimal(batch_count),
        occurred_at=get_datetime_utc(),
    )


def test_order_copies_card_lines_scaled_by_batch() -> None:
    order = make_order("2")

    assert order.status is ProductionOrderStatus.DRAFT
    assert order.components[0].planned_quantity == Decimal(200)
    assert order.components[0].actual_quantity == Decimal(200)
    assert order.outputs[0].planned_quantity == Decimal(80)


def test_zero_batch_is_rejected() -> None:
    with pytest.raises(EmptyBatchError):
        make_order("0")


def test_post_makes_losses_equal_to_residual() -> None:
    order = make_order()


    actual_output = order.outputs[0].actual_quantity - Decimal(4)
    order.set_actual(order.outputs[0].id, actual_output)
    order.post()

    assert order.status is ProductionOrderStatus.POSTED
    assert order.posted_at is not None

    inputs = sum((line.actual_quantity for line in order.components), Decimal(0))
    outputs = sum((line.actual_quantity for line in order.outputs), Decimal(0))
    losses = sum((line.actual_quantity for line in order.losses), Decimal(0))

    assert losses == inputs - outputs
    assert losses == Decimal(34)


def test_losses_are_split_between_planned_kinds() -> None:
    card = TechCard.create(
        code="SMOKE",
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=[
            TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(100)),
            TechCardLine.output(nomenclature_id=uuid4(), quantity=Decimal(100)),
            TechCardLine.loss(loss_kind=LossKind.SHRINKAGE, quantity=Decimal(8)),
            TechCardLine.loss(loss_kind=LossKind.COOKING, quantity=Decimal(2)),
        ],
    )
    order = ProductionOrder.create(
        warehouse_id=uuid4(),
        tech_card=card,
        batch_count=Decimal(1),
        occurred_at=get_datetime_utc(),
    )
    order.set_actual(order.outputs[0].id, Decimal(85))
    order.post()

    shares = {line.loss_kind: line.actual_quantity for line in order.losses}

    assert sum(shares.values(), Decimal(0)) == Decimal(15)
    assert shares[LossKind.SHRINKAGE] > shares[LossKind.COOKING]


def test_output_above_input_is_rejected() -> None:
    order = make_order()
    order.set_actual(order.outputs[0].id, Decimal(500))

    with pytest.raises(OutputExceedsInputError):
        order.post()


def test_order_without_output_is_rejected() -> None:
    order = make_order()
    for line in order.outputs:
        order.set_actual(line.id, Decimal(0))

    with pytest.raises(EmptyProductionOutputError):
        order.post()


def test_posted_order_cannot_be_changed() -> None:
    order = make_order()
    order.post()

    with pytest.raises(ProductionOrderNotDraftError):
        order.set_actual(order.outputs[0].id, Decimal(1))

    with pytest.raises(ProductionOrderNotDraftError):
        order.cancel()


def test_unknown_line_is_rejected() -> None:
    order = make_order()

    with pytest.raises(ProductionOrderLineNotFoundError):
        order.set_actual(uuid4(), Decimal(1))


def test_cancel_marks_draft_as_cancelled() -> None:
    order = make_order()
    order.cancel()

    assert order.status is ProductionOrderStatus.CANCELLED


def test_costs_are_applied_to_output_lines() -> None:
    order = make_order()
    order.post()
    output = order.outputs[0]

    order.apply_costs({output.id: 12345})

    assert order.outputs[0].cost_kopecks == 12345
