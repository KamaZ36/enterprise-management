from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.update import (
    UpdateReceiptCommand,
    UpdateReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.update import (
    UpdateWriteOffCommand,
    UpdateWriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)
from tests.modules.inventory.helpers import build_interactors

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


async def balance_row(
    db_session: AsyncSession, org_unit_id: UUID, nomenclature_id: UUID
):
    return (
        await db_session.execute(
            text(
                "select quantity, total_value from inventory.stock_balances"
                " where org_unit_id = :org_unit_id"
                " and nomenclature_id = :nomenclature_id"
            ),
            {"org_unit_id": org_unit_id, "nomenclature_id": nomenclature_id},
        )
    ).one_or_none()


async def test_update_receipt_draft_replaces_lines_and_header(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            supplier_name="Старый",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(450),
                )
            ],
        )
    )

    await interactors.update_receipt(
        UpdateReceiptCommand(
            receipt_id=receipt_id,
            occurred_at=OCCURRED_AT,
            supplier_name="Новый",
            supplier_document_number="УПД-7",
            comment="Поправили",
            lines=[
                UpdateReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(4),
                    unit_cost=Decimal(100),
                    lot_code="L-NEW",
                )
            ],
        )
    )

    stored = await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id)
    assert stored is not None
    assert stored.supplier_name == "Новый"
    assert stored.supplier_document_number == "УПД-7"
    assert stored.comment == "Поправили"
    assert [line.quantity for line in stored.lines] == [Decimal(4)]
    assert stored.lines[0].lot_code == "L-NEW"

    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    row = await balance_row(db_session, location.id, nomenclature.id)
    assert row is not None
    assert row.quantity == Decimal(4)
    assert row.total_value == 40000


async def test_update_receipt_after_post_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                    unit_cost=Decimal(10),
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    with pytest.raises(DocumentAlreadyPostedError):
        await interactors.update_receipt(
            UpdateReceiptCommand(
                receipt_id=receipt_id,
                occurred_at=OCCURRED_AT,
                lines=[
                    UpdateReceiptLineCommand(
                        nomenclature_id=nomenclature.id,
                        quantity=Decimal(2),
                        unit_cost=Decimal(20),
                    )
                ],
            )
        )


async def test_update_receipt_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    receipt_id = await build_interactors(db_session).create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                    unit_cost=Decimal(10),
                )
            ],
        )
    )

    denied = build_interactors(db_session, allowed=False)
    with pytest.raises(ForbiddenError):
        await denied.update_receipt(
            UpdateReceiptCommand(
                receipt_id=receipt_id,
                occurred_at=OCCURRED_AT,
                lines=[
                    UpdateReceiptLineCommand(
                        nomenclature_id=nomenclature.id,
                        quantity=Decimal(2),
                        unit_cost=Decimal(20),
                    )
                ],
            )
        )


async def test_update_write_off_draft_replaces_lines(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(500),
                    lot_code="L-1",
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            reason="Старая причина",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(2),
                    lot_code="L-1",
                )
            ],
        )
    )

    await interactors.update_write_off(
        UpdateWriteOffCommand(
            write_off_id=write_off_id,
            occurred_at=OCCURRED_AT,
            reason="Просрочка",
            comment="Уточнили",
            lines=[
                UpdateWriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(6),
                    lot_code="L-1",
                )
            ],
        )
    )

    stored = await SQLAlchemyWriteOffRepository(db_session).get_by_id(write_off_id)
    assert stored is not None
    assert stored.reason == "Просрочка"
    assert stored.comment == "Уточнили"
    assert [line.quantity for line in stored.lines] == [Decimal(6)]

    await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))

    row = await balance_row(db_session, location.id, nomenclature.id)
    assert row is not None
    assert row.quantity == Decimal(4)


async def test_update_write_off_after_post_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(500),
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id, quantity=Decimal(1)
                )
            ],
        )
    )
    await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))

    with pytest.raises(DocumentAlreadyPostedError):
        await interactors.update_write_off(
            UpdateWriteOffCommand(
                write_off_id=write_off_id,
                occurred_at=OCCURRED_AT,
                lines=[
                    UpdateWriteOffLineCommand(
                        nomenclature_id=nomenclature.id, quantity=Decimal(2)
                    )
                ],
            )
        )


async def test_update_write_off_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    write_off_id = await build_interactors(db_session).create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id, quantity=Decimal(1)
                )
            ],
        )
    )

    denied = build_interactors(db_session, allowed=False)
    with pytest.raises(ForbiddenError):
        await denied.update_write_off(
            UpdateWriteOffCommand(
                write_off_id=write_off_id,
                occurred_at=OCCURRED_AT,
                lines=[
                    UpdateWriteOffLineCommand(
                        nomenclature_id=nomenclature.id, quantity=Decimal(2)
                    )
                ],
            )
        )
