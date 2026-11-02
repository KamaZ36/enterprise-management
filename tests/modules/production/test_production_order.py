from datetime import date
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
    VetisReferenceRequiredError,
    WrongProductionLineRoleError,
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
from myasnaya_derevnya.modules.production.domain.value_objects.vetis_status import (
    VetisStatus,
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
        org_unit_id=uuid4(),
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


def test_component_lot_and_output_expiry_are_stored() -> None:
    order = make_order()
    lot_id = uuid4()
    expires_at = date(2026, 12, 31)

    order.set_lot(order.components[0].id, lot_id)
    order.set_expires_at(order.outputs[0].id, expires_at)

    assert order.components[0].lot_id == lot_id
    assert order.outputs[0].expires_at == expires_at


def test_lot_cannot_be_set_on_output() -> None:
    order = make_order()

    with pytest.raises(WrongProductionLineRoleError):
        order.set_lot(order.outputs[0].id, uuid4())


def test_expiry_cannot_be_set_on_component() -> None:
    order = make_order()

    with pytest.raises(WrongProductionLineRoleError):
        order.set_expires_at(order.components[0].id, date(2026, 12, 31))


def test_traceability_is_frozen_after_post() -> None:
    order = make_order()
    order.post()

    with pytest.raises(ProductionOrderNotDraftError):
        order.set_lot(order.components[0].id, uuid4())
    with pytest.raises(ProductionOrderNotDraftError):
        order.set_expires_at(order.outputs[0].id, date(2026, 12, 31))


def test_manual_vetis_requires_operation_id() -> None:
    order = make_order()

    with pytest.raises(VetisReferenceRequiredError):
        order.set_vetis(
            status=VetisStatus.MANUAL,
            operation_id=None,
            no_vsd_reason=None,
            entered_by=uuid4(),
        )


def test_vetis_can_be_set_after_posting() -> None:
    order = make_order()
    order.post()
    order.set_vetis(
        status=VetisStatus.MANUAL,
        operation_id="OP-42",
        no_vsd_reason=None,
        entered_by=uuid4(),
    )

    assert order.vetis_status is VetisStatus.MANUAL
    assert order.vetis_operation_id == "OP-42"
    assert order.vetis_entered_at is not None


def test_no_vsd_clears_operation() -> None:
    order = make_order()
    order.set_vetis(
        status=VetisStatus.MANUAL,
        operation_id="OP-42",
        no_vsd_reason=None,
        entered_by=uuid4(),
    )
    order.set_vetis(
        status=VetisStatus.NO_VSD,
        operation_id=None,
        no_vsd_reason="Домашний производитель",
        entered_by=uuid4(),
    )

    assert order.vetis_operation_id is None
    assert order.vetis_no_vsd_reason == "Домашний производитель"


def test_output_vetis_is_stored_on_output_line() -> None:
    order = make_order()
    vsd_guid = uuid4()

    order.set_output_vetis(
        line_id=order.outputs[0].id,
        production_vsd_guid=vsd_guid,
        batch_id="BATCH-1",
    )

    assert order.outputs[0].vetis_production_vsd_guid == vsd_guid
    assert order.outputs[0].vetis_batch_id == "BATCH-1"


def test_output_vetis_is_rejected_for_component() -> None:
    order = make_order()

    with pytest.raises(WrongProductionLineRoleError):
        order.set_output_vetis(
            line_id=order.components[0].id,
            production_vsd_guid=uuid4(),
            batch_id=None,
        )


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
        org_unit_id=uuid4(),
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
