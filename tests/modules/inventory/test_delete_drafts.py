from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.create import (
    CreateInventoryCountCommand,
    CreateInventoryCountInteractor,
    InventoryCountLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.delete import (
    DeleteInventoryCountCommand,
    DeleteInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.delete import (
    DeleteReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.create import (
    CreateTransferCommand,
    CreateTransferInteractor,
    TransferLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.delete import (
    DeleteTransferCommand,
    DeleteTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.delete import (
    DeleteWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCount,
    InventoryCountLine,
)
from myasnaya_derevnya.modules.inventory.domain.entities.receipt import (
    Receipt,
    ReceiptLine,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.entities.write_off import (
    WriteOff,
    WriteOffLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InventoryCountNotFoundError,
    ReceiptNotFoundError,
    TransferNotFoundError,
    WriteOffNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.sqlalchemy import (
    SQLAlchemyInventoryCountRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.sqlalchemy import (
    SQLAlchemyTransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)
from tests.modules.inventory.helpers import (
    FakeIdentityProvider,
    FakeStaffAPI,
    build_interactors,
    business_api,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


async def count_lines(
    db_session: AsyncSession, table: str, column: str, document_id: UUID
) -> int:
    return (
        await db_session.execute(
            text(f"select count(*) from inventory.{table} where {column} = :id"),
            {"id": document_id},
        )
    ).scalar_one()


def build_transfer_interactors(
    session: AsyncSession, *, allowed: bool = True
) -> tuple[CreateTransferInteractor, DeleteTransferInteractor]:
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI(allowed=allowed)
    transaction_manager = SQLAlchemyTransactionManager(session)
    api = business_api(session)
    repository = SQLAlchemyTransferRepository(session)

    return (
        CreateTransferInteractor(
            identity_provider=identity,
            business_api=api,
            transfer_repository=repository,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
        DeleteTransferInteractor(
            identity_provider=identity,
            business_api=api,
            transfer_repository=repository,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
    )


def build_inventory_count_interactors(
    session: AsyncSession, *, allowed: bool = True
) -> tuple[CreateInventoryCountInteractor, DeleteInventoryCountInteractor]:
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI(allowed=allowed)
    transaction_manager = SQLAlchemyTransactionManager(session)
    api = business_api(session)
    repository = SQLAlchemyInventoryCountRepository(session)

    return (
        CreateInventoryCountInteractor(
            identity_provider=identity,
            business_api=api,
            inventory_count_repository=repository,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
        DeleteInventoryCountInteractor(
            identity_provider=identity,
            business_api=api,
            inventory_count_repository=repository,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
    )


async def stored_receipt(db_session: AsyncSession, receipt: Receipt) -> None:
    await SQLAlchemyReceiptRepository(db_session).add(receipt)


async def stored_write_off(db_session: AsyncSession, write_off: WriteOff) -> None:
    await SQLAlchemyWriteOffRepository(db_session).add(write_off)


async def stored_transfer(db_session: AsyncSession, transfer: Transfer) -> None:
    await SQLAlchemyTransferRepository(db_session).add(transfer)


async def stored_inventory_count(
    db_session: AsyncSession, inventory_count: InventoryCount
) -> None:
    await SQLAlchemyInventoryCountRepository(db_session).add(inventory_count)


# --- Поступления ------------------------------------------------------------


async def test_delete_receipt_draft_removes_document_and_lines(
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
                    quantity=Decimal(3),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )

    await interactors.delete_receipt(DeleteReceiptCommand(receipt_id=receipt_id))

    assert await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id) is None
    assert await count_lines(db_session, "receipt_lines", "receipt_id", receipt_id) == 0


async def test_delete_receipt_draft_twice_is_not_found(
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
    await interactors.delete_receipt(DeleteReceiptCommand(receipt_id=receipt_id))

    with pytest.raises(ReceiptNotFoundError):
        await interactors.delete_receipt(DeleteReceiptCommand(receipt_id=receipt_id))


async def test_delete_posted_receipt_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    receipt = Receipt.create(
        org_unit_id=location.id,
        occurred_at=OCCURRED_AT,
        lines=[
            ReceiptLine.create(
                nomenclature_id=nomenclature.id,
                quantity=Decimal(2),
                unit_cost=Decimal(250),
            )
        ],
    )
    receipt.post()
    await stored_receipt(db_session, receipt)

    with pytest.raises(DocumentAlreadyPostedError):
        await interactors.delete_receipt(DeleteReceiptCommand(receipt_id=receipt.id))

    assert await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt.id) is not None


async def test_delete_receipt_requires_permission(
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
        await denied.delete_receipt(DeleteReceiptCommand(receipt_id=receipt_id))

    assert await SQLAlchemyReceiptRepository(db_session).get_by_id(receipt_id) is not None


# --- Списания ---------------------------------------------------------------


async def test_delete_write_off_draft_removes_document_and_lines(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            reason="Просрочка",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(2),
                )
            ],
        )
    )

    await interactors.delete_write_off(
        DeleteWriteOffCommand(write_off_id=write_off_id)
    )

    repository = SQLAlchemyWriteOffRepository(db_session)
    assert await repository.get_by_id(write_off_id) is None
    assert (
        await count_lines(db_session, "write_off_lines", "write_off_id", write_off_id)
        == 0
    )


async def test_delete_write_off_after_post_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    write_off = WriteOff.create(
        org_unit_id=location.id,
        occurred_at=OCCURRED_AT,
        reason="Брак",
        lines=[
            WriteOffLine.create(
                nomenclature_id=nomenclature.id,
                quantity=Decimal(1),
            )
        ],
    )
    write_off.post()
    await stored_write_off(db_session, write_off)

    with pytest.raises(DocumentAlreadyPostedError):
        await interactors.delete_write_off(
            DeleteWriteOffCommand(write_off_id=write_off.id)
        )


async def test_delete_write_off_requires_permission(
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
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                )
            ],
        )
    )

    denied = build_interactors(db_session, allowed=False)
    with pytest.raises(ForbiddenError):
        await denied.delete_write_off(
            DeleteWriteOffCommand(write_off_id=write_off_id)
        )


# --- Перемещения ------------------------------------------------------------


async def test_delete_transfer_draft_removes_document_and_lines(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    source = await make_location()
    target = await make_location()
    nomenclature = await make_nomenclature()

    create, delete = build_transfer_interactors(db_session)
    transfer_id = await create(
        CreateTransferCommand(
            from_org_unit_id=source.id,
            to_org_unit_id=target.id,
            occurred_at=OCCURRED_AT,
            lines=[
                TransferLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(2),
                )
            ],
        )
    )

    await delete(DeleteTransferCommand(transfer_id=transfer_id))

    repository = SQLAlchemyTransferRepository(db_session)
    assert await repository.get_by_id(transfer_id) is None
    assert (
        await count_lines(db_session, "transfer_lines", "transfer_id", transfer_id)
        == 0
    )


async def test_delete_posted_transfer_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    source = await make_location()
    target = await make_location()
    nomenclature = await make_nomenclature()

    transfer = Transfer.create(
        from_org_unit_id=source.id,
        to_org_unit_id=target.id,
        occurred_at=OCCURRED_AT,
        lines=[
            TransferLine.create(
                nomenclature_id=nomenclature.id,
                quantity=Decimal(1),
            )
        ],
    )
    transfer.post()
    await stored_transfer(db_session, transfer)

    _, delete = build_transfer_interactors(db_session)
    with pytest.raises(DocumentAlreadyPostedError):
        await delete(DeleteTransferCommand(transfer_id=transfer.id))


async def test_delete_transfer_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    source = await make_location()
    target = await make_location()
    nomenclature = await make_nomenclature()

    create, _ = build_transfer_interactors(db_session)
    transfer_id = await create(
        CreateTransferCommand(
            from_org_unit_id=source.id,
            to_org_unit_id=target.id,
            occurred_at=OCCURRED_AT,
            lines=[
                TransferLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                )
            ],
        )
    )

    _, denied = build_transfer_interactors(db_session, allowed=False)
    with pytest.raises(ForbiddenError):
        await denied(DeleteTransferCommand(transfer_id=transfer_id))


# --- Инвентаризации ---------------------------------------------------------


async def test_delete_inventory_count_draft_removes_document_and_lines(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    create, delete = build_inventory_count_interactors(db_session)
    count_id = await create(
        CreateInventoryCountCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                InventoryCountLineCommand(
                    nomenclature_id=nomenclature.id,
                    counted_quantity=Decimal(5),
                )
            ],
        )
    )

    await delete(DeleteInventoryCountCommand(inventory_count_id=count_id))

    repository = SQLAlchemyInventoryCountRepository(db_session)
    assert await repository.get_by_id(count_id) is None
    assert (
        await count_lines(
            db_session, "inventory_count_lines", "inventory_count_id", count_id
        )
        == 0
    )


async def test_delete_posted_inventory_count_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    inventory_count = InventoryCount.create(
        org_unit_id=location.id,
        occurred_at=OCCURRED_AT,
        lines=[
            InventoryCountLine.create(
                nomenclature_id=nomenclature.id,
                counted_quantity=Decimal(1),
            )
        ],
    )
    inventory_count.post()
    await stored_inventory_count(db_session, inventory_count)

    _, delete = build_inventory_count_interactors(db_session)
    with pytest.raises(DocumentAlreadyPostedError):
        await delete(
            DeleteInventoryCountCommand(inventory_count_id=inventory_count.id)
        )


async def test_delete_inventory_count_requires_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    create, _ = build_inventory_count_interactors(db_session)
    count_id = await create(
        CreateInventoryCountCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                InventoryCountLineCommand(
                    nomenclature_id=nomenclature.id,
                    counted_quantity=Decimal(1),
                )
            ],
        )
    )

    _, denied = build_inventory_count_interactors(db_session, allowed=False)
    with pytest.raises(ForbiddenError):
        await denied(DeleteInventoryCountCommand(inventory_count_id=count_id))


async def test_delete_inventory_count_twice_is_not_found(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()

    create, delete = build_inventory_count_interactors(db_session)
    count_id = await create(
        CreateInventoryCountCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                InventoryCountLineCommand(
                    nomenclature_id=nomenclature.id,
                    counted_quantity=Decimal(1),
                )
            ],
        )
    )
    await delete(DeleteInventoryCountCommand(inventory_count_id=count_id))

    with pytest.raises(InventoryCountNotFoundError):
        await delete(DeleteInventoryCountCommand(inventory_count_id=count_id))


async def test_delete_transfer_twice_is_not_found(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    source = await make_location()
    target = await make_location()
    nomenclature = await make_nomenclature()

    create, delete = build_transfer_interactors(db_session)
    transfer_id = await create(
        CreateTransferCommand(
            from_org_unit_id=source.id,
            to_org_unit_id=target.id,
            occurred_at=OCCURRED_AT,
            lines=[
                TransferLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                )
            ],
        )
    )
    await delete(DeleteTransferCommand(transfer_id=transfer_id))

    with pytest.raises(TransferNotFoundError):
        await delete(DeleteTransferCommand(transfer_id=transfer_id))


async def test_delete_write_off_twice_is_not_found(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    interactors = build_interactors(db_session)

    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                )
            ],
        )
    )
    await interactors.delete_write_off(
        DeleteWriteOffCommand(write_off_id=write_off_id)
    )

    with pytest.raises(WriteOffNotFoundError):
        await interactors.delete_write_off(
            DeleteWriteOffCommand(write_off_id=write_off_id)
        )
