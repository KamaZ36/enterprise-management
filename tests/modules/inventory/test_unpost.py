from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.create import (
    CreateOpeningBalanceCommand,
    OpeningBalanceLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.post import (
    PostOpeningBalanceCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.unpost import (
    UnpostOpeningBalanceCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.unpost import (
    UnpostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.unpost import (
    UnpostWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentCannotBeUnpostedError,
    DocumentNotPostedError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.sqlalchemy import (
    SQLAlchemyOpeningBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)
from tests.modules.inventory.helpers import (
    build_interactors,
    build_opening_balance_actors,
    build_unpost_actors,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


async def balance_row(
    session: AsyncSession, org_unit_id: UUID, nomenclature_id: UUID
):
    return (
        await session.execute(
            text(
                "select quantity, total_value from inventory.stock_balances"
                " where org_unit_id = :org_unit_id"
                " and nomenclature_id = :nomenclature_id"
            ),
            {
                "org_unit_id": org_unit_id,
                "nomenclature_id": nomenclature_id,
            },
        )
    ).one_or_none()


async def movement_count(session: AsyncSession, nomenclature_id: UUID) -> int:
    return (
        await session.scalar(
            text(
                "select count(*) from inventory.stock_movements"
                " where nomenclature_id = :nomenclature_id"
            ),
            {"nomenclature_id": nomenclature_id},
        )
    ) or 0


async def posting_count(session: AsyncSession, document_id: UUID) -> int:
    return (
        await session.scalar(
            text(
                "select count(*) from inventory.stock_postings"
                " where document_id = :document_id"
            ),
            {"document_id": document_id},
        )
    ) or 0


async def create_posted_receipt(
    session: AsyncSession, org_unit_id: UUID, nomenclature_id: UUID
):
    actors = build_interactors(session)
    receipt_id = await actors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )
    await actors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))
    return receipt_id


async def test_unpost_receipt_restores_balance_and_status(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    receipt_id = await create_posted_receipt(
        db_session, location.id, nomenclature.id
    )

    unpost = build_unpost_actors(db_session)
    await unpost.receipt(UnpostReceiptCommand(receipt_id=receipt_id))

    stored = await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id)
    assert stored is not None
    assert stored.status is DocumentStatus.DRAFT
    assert stored.posted_at is None

    balance = await balance_row(db_session, location.id, nomenclature.id)
    assert balance is not None
    assert balance.quantity == Decimal(0)
    assert balance.total_value == 0

    assert await movement_count(db_session, nomenclature.id) == 0
    assert await posting_count(db_session, receipt_id) == 0

    # После отмены документ можно провести снова.
    actors = build_interactors(db_session)
    await actors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    restored = await balance_row(db_session, location.id, nomenclature.id)
    assert restored is not None
    assert restored.quantity == Decimal(10)
    assert restored.total_value == 100000


async def test_unpost_receipt_is_blocked_when_stock_consumed(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    receipt_id = await create_posted_receipt(
        db_session, location.id, nomenclature.id
    )

    actors = build_interactors(db_session)
    write_off_id = await actors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            reason="Порча",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(4),
                )
            ],
        )
    )
    await actors.post_write_off(
        PostWriteOffCommand(write_off_id=write_off_id)
    )

    unpost = build_unpost_actors(db_session)

    with pytest.raises(DocumentCannotBeUnpostedError):
        await unpost.receipt(UnpostReceiptCommand(receipt_id=receipt_id))

    stored = await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id)
    assert stored is not None
    assert stored.status is DocumentStatus.POSTED

    balance = await balance_row(db_session, location.id, nomenclature.id)
    assert balance is not None
    assert balance.quantity == Decimal(6)


async def test_unpost_write_off_returns_stock_and_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    await create_posted_receipt(db_session, location.id, nomenclature.id)

    actors = build_interactors(db_session)
    write_off_id = await actors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            reason="Порча",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(4),
                )
            ],
        )
    )
    await actors.post_write_off(
        PostWriteOffCommand(write_off_id=write_off_id)
    )

    unpost = build_unpost_actors(db_session)
    await unpost.write_off(
        UnpostWriteOffCommand(write_off_id=write_off_id)
    )

    stored = await SQLAlchemyWriteOffRepository(db_session).get_by_id(
        write_off_id
    )
    assert stored is not None
    assert stored.status is DocumentStatus.DRAFT

    balance = await balance_row(db_session, location.id, nomenclature.id)
    assert balance is not None
    assert balance.quantity == Decimal(10)
    assert balance.total_value == 100000
    assert await movement_count(db_session, nomenclature.id) == 1


async def test_unpost_opening_balance_clears_stock(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    actors = build_opening_balance_actors(db_session)

    document_id = await actors.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(5),
                    unit_cost=Decimal(200),
                )
            ],
        )
    )
    await actors.post(
        PostOpeningBalanceCommand(opening_balance_id=document_id)
    )

    unpost = build_unpost_actors(db_session)
    await unpost.opening_balance(
        UnpostOpeningBalanceCommand(opening_balance_id=document_id)
    )

    stored = await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(
        document_id
    )
    assert stored is not None
    assert stored.status is DocumentStatus.DRAFT

    balance = await balance_row(db_session, location.id, nomenclature.id)
    assert balance is not None
    assert balance.quantity == Decimal(0)
    assert balance.total_value == 0
    assert await movement_count(db_session, nomenclature.id) == 0


async def test_unpost_draft_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    actors = build_interactors(db_session)

    receipt_id = await actors.create_receipt(
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

    unpost = build_unpost_actors(db_session)

    with pytest.raises(DocumentNotPostedError):
        await unpost.receipt(UnpostReceiptCommand(receipt_id=receipt_id))


async def test_unpost_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    receipt_id = await create_posted_receipt(
        db_session, location.id, nomenclature.id
    )

    denied = build_unpost_actors(db_session, allowed=False)

    with pytest.raises(ForbiddenError):
        await denied.receipt(UnpostReceiptCommand(receipt_id=receipt_id))

    stored = await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id)
    assert stored is not None
    assert stored.status is DocumentStatus.POSTED

async def test_unpost_is_blocked_when_later_movements_exist(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    receipt_id = await create_posted_receipt(
        db_session, location.id, nomenclature.id
    )

    actors = build_interactors(db_session)
    second_id = await actors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(5),
                    unit_cost=Decimal(50),
                )
            ],
        )
    )
    await actors.post_receipt(PostReceiptCommand(receipt_id=second_id))

    unpost = build_unpost_actors(db_session)

    with pytest.raises(DocumentCannotBeUnpostedError):
        await unpost.receipt(UnpostReceiptCommand(receipt_id=receipt_id))

    # Второй документ по-прежнему можно отменить: после него движений нет.
    await unpost.receipt(UnpostReceiptCommand(receipt_id=second_id))

    stored = await SQLAlchemyReceiptRepository(db_session).get_by_id(second_id)
    assert stored is not None
    assert stored.status is DocumentStatus.DRAFT

