"""Интеграционные тесты проведения документов на настоящем PostgreSQL."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.connection import async_session_maker
from myasnaya_derevnya.core.errors import ConflictError
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
)
from myasnaya_derevnya.modules.inventory.application.commands import (
    ReceiptLineCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_receipt import (
    CreateReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_write_off import (
    CreateWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_receipt import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_write_off import (
    PostWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InsufficientLotStockError,
    InsufficientStockError,
    NomenclatureNotAllowedInWarehouseError,
    NomenclatureNotFoundError,
    StockLotNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from tests.modules.inventory.helpers import build_interactors, movement_totals

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _sqlstate(exc: DBAPIError) -> str | None:
    orig = getattr(exc, "orig", None)
    cause = getattr(orig, "__cause__", None) or orig
    return getattr(cause, "sqlstate", None)


async def receive(
    db_session: AsyncSession,
    warehouse_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    unit_cost: str,
    lot_code: str | None = None,
    expires_at: date | None = None,
) -> UUID:
    """Создаёт и сразу проводит поступление."""
    interactors = build_interactors(db_session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse_id,
            occurred_at=OCCURRED_AT,
            supplier_name="Мясокомбинат",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                    lot_code=lot_code,
                    expires_at=expires_at,
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    return receipt_id


async def write_off(
    db_session: AsyncSession,
    warehouse_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    lot_code: str | None = None,
) -> UUID:
    interactors = build_interactors(db_session)
    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            warehouse_id=warehouse_id,
            occurred_at=OCCURRED_AT,
            reason="Просрочка",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    lot_code=lot_code,
                )
            ],
        )
    )
    await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))

    return write_off_id


async def balance_of(
    db_session: AsyncSession, warehouse_id: UUID, nomenclature_id: UUID
):
    repository = SQLAlchemyStockBalanceRepository(db_session)

    return await repository.get(warehouse_id, nomenclature_id)


async def test_receipt_matches_movement_sum(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, warehouse.id, nomenclature.id, "10", "450")

    balance = await balance_of(db_session, warehouse.id, nomenclature.id)
    movements_quantity, movements_cost = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    assert balance.quantity == Decimal(10)
    assert balance.total_value.kopecks == 450000
    assert balance.average_unit_cost == Decimal(450)
    assert movements_quantity == balance.quantity
    assert movements_cost == balance.total_value.kopecks


async def test_moving_average_across_two_receipts(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, warehouse.id, nomenclature.id, "10", "450")
    await receive(db_session, warehouse.id, nomenclature.id, "5", "480")
    await write_off(db_session, warehouse.id, nomenclature.id, "3")

    balance = await balance_of(db_session, warehouse.id, nomenclature.id)
    movements_quantity, movements_cost = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    # средняя: (450000 + 240000) / 15 = 46000 копеек за кг
    assert balance.quantity == Decimal(12)
    assert balance.total_value.kopecks == 552000
    assert movements_cost == 552000
    assert movements_quantity == Decimal(12)


async def test_full_write_off_leaves_no_residue(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    """3 единицы за 100 копеек: средняя нацело не делится."""
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, warehouse.id, nomenclature.id, "3", "0.333333")

    for _ in range(3):
        await write_off(db_session, warehouse.id, nomenclature.id, "1")

    balance = await balance_of(db_session, warehouse.id, nomenclature.id)
    movements_quantity, movements_cost = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    assert balance.quantity == Decimal(0)
    assert balance.total_value.kopecks == 0
    assert movements_quantity == Decimal(0)
    assert movements_cost == 0


async def test_write_off_beyond_stock_is_rejected(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "2", "100")

    interactors = build_interactors(db_session)
    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id, quantity=Decimal("2.5")
                )
            ],
        )
    )

    with pytest.raises(InsufficientStockError):
        await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))

    # В приложении откат делает провайдер сессии; здесь сессия наша, откатываем вручную.
    await db_session.rollback()

    balance = await balance_of(db_session, warehouse.id, nomenclature.id)
    movements_quantity, _ = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    assert balance.quantity == Decimal(2)
    assert movements_quantity == Decimal(2)


async def test_document_is_posted_only_once(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()
    receipt_id = await receive(db_session, warehouse.id, nomenclature.id, "5", "100")

    interactors = build_interactors(db_session)

    with pytest.raises(DocumentAlreadyPostedError):
        await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    await db_session.rollback()

    balance = await balance_of(db_session, warehouse.id, nomenclature.id)
    movements_quantity, _ = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    assert balance.quantity == Decimal(5)
    assert movements_quantity == Decimal(5)


async def test_double_posting_is_blocked_by_database(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    """Даже если проверку статуса обойти, уникальность пары не даст провести дважды.

    Так выглядел бы гонка: два запроса одновременно увидели черновик.
    """
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()
    receipt_id = await receive(db_session, warehouse.id, nomenclature.id, "5", "100")

    # Имитируем гонку: статус снова черновик, хотя проведение уже существует.
    await db_session.execute(
        text("update inventory.receipts set status = 'draft' where id = :id"),
        {"id": receipt_id},
    )
    await db_session.commit()

    interactors = build_interactors(db_session)

    with pytest.raises(ConflictError):
        await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    await db_session.rollback()

    postings = await db_session.scalar(
        text(
            "select count(*) from inventory.stock_postings"
            " where document_type = 'receipt' and document_id = :id"
        ),
        {"id": receipt_id},
    )
    movements_quantity, _ = await movement_totals(
        db_session, warehouse.id, nomenclature.id
    )

    assert postings == 1
    assert movements_quantity == Decimal(5)


async def test_nomenclature_type_must_match_warehouse(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse(type_=WarehouseType.RAW)
    finished = await make_nomenclature(type_=NomenclatureType.FINISHED_GOOD)

    interactors = build_interactors(db_session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=finished.id,
                    quantity=Decimal(1),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )

    with pytest.raises(NomenclatureNotAllowedInWarehouseError):
        await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    await db_session.rollback()

    assert await balance_of(db_session, warehouse.id, finished.id) is None


async def test_unknown_nomenclature_is_rejected(
    db_session: AsyncSession, make_warehouse
) -> None:
    warehouse = await make_warehouse()

    interactors = build_interactors(db_session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=uuid4(),
                    quantity=Decimal(1),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )

    with pytest.raises(NomenclatureNotFoundError):
        await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    await db_session.rollback()


async def test_write_off_of_unknown_lot_is_rejected(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    """Списание не заводит партии: списать то, чего не было, нельзя."""
    warehouse = await make_warehouse()
    meat = await make_nomenclature()
    await receive(db_session, warehouse.id, meat.id, "5", "100")

    interactors = build_interactors(db_session)
    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=meat.id,
                    quantity=Decimal(1),
                    lot_code="НЕТ-ТАКОЙ",
                )
            ],
        )
    )

    with pytest.raises(StockLotNotFoundError):
        await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))

    await db_session.rollback()


async def test_lot_balances_are_tracked(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    meat = await make_nomenclature()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        "8",
        "500",
        lot_code="L-001",
        expires_at=date(2026, 10, 20),
    )
    await receive(db_session, warehouse.id, meat.id, "8", "500", lot_code="L-002")
    await write_off(db_session, warehouse.id, meat.id, "3", lot_code="L-001")

    lot_rows = (
        await db_session.execute(
            text(
                "select id, lot_code, expires_at from inventory.stock_lots"
                " where nomenclature_id = :nomenclature_id"
                " order by lot_code"
            ),
            {"nomenclature_id": meat.id},
        )
    ).all()
    lot_balance = (
        await db_session.execute(
            text(
                "select quantity from inventory.stock_lot_balances"
                " where lot_id = :lot_id"
            ),
            {"lot_id": lot_rows[0].id},
        )
    ).one()

    assert [row.lot_code for row in lot_rows] == ["L-001", "L-002"]
    assert lot_rows[0].expires_at == date(2026, 10, 20)
    assert lot_balance.quantity == Decimal(5)

    # Всего на складе 13, но в партии L-001 только 5: списать 6 нельзя
    with pytest.raises(InsufficientLotStockError):
        await write_off(db_session, warehouse.id, meat.id, "6", lot_code="L-001")

    await db_session.rollback()

    balance = await balance_of(db_session, warehouse.id, meat.id)
    assert balance.quantity == Decimal(13)


async def test_balance_row_is_locked_during_posting(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    """Строка баланса обязана быть под FOR UPDATE.

    Проверка «два параллельных прихода» сама по себе этого не доказывает: без
    блокировки транзакции могут разойтись по времени. Поэтому проверяем саму
    блокировку — вторая транзакция не должна получить ту же строку.
    """
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()
    repository = SQLAlchemyStockBalanceRepository(db_session)

    await repository.lock_many([(warehouse.id, nomenclature.id)])
    await db_session.commit()

    # Вторая транзакция этой же сессии держит строку до конца теста.
    await repository.lock_many([(warehouse.id, nomenclature.id)])

    async with async_session_maker() as other:
        with pytest.raises(DBAPIError) as error:
            await other.execute(
                text(
                    "select 1 from inventory.stock_balances"
                    " where warehouse_id = :warehouse_id"
                    " and nomenclature_id = :nomenclature_id"
                    " for update nowait"
                ),
                {"warehouse_id": warehouse.id, "nomenclature_id": nomenclature.id},
            )

    assert _sqlstate(error.value) == "55P03"


async def test_concurrent_receipts_are_not_lost(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    """Два параллельных прихода на одну пару дают правильный итог.

    Строку баланса создаём заранее: иначе обе транзакции сериализуются на
    вставке и потеря обновления не воспроизведётся.
    """
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "1", "1")

    async def post_in_own_session(quantity: str, unit_cost: str) -> None:
        async with async_session_maker() as session:
            await receive(session, warehouse.id, nomenclature.id, quantity, unit_cost)

    await asyncio.gather(
        post_in_own_session("5", "100"),
        post_in_own_session("7", "110"),
    )

    async with async_session_maker() as session:
        balance = await balance_of(session, warehouse.id, nomenclature.id)
        movements_quantity, movements_cost = await movement_totals(
            session, warehouse.id, nomenclature.id
        )

    assert balance.quantity == Decimal(13)
    assert balance.total_value.kopecks == 100 + 50000 + 77000
    assert movements_quantity == Decimal(13)
    assert movements_cost == 100 + 50000 + 77000
