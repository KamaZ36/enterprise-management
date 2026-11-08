from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.create import (
    CreateOpeningBalanceCommand,
    OpeningBalanceLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.delete import (
    DeleteOpeningBalanceCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.post import (
    PostOpeningBalanceCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.update import (
    UpdateOpeningBalanceCommand,
    UpdateOpeningBalanceLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.entities.opening_balance import (
    OpeningBalance,
    OpeningBalanceLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    NegativeCostError,
    OpeningBalanceNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.opening_balance.sqlalchemy import (
    SQLAlchemyOpeningBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.sqlalchemy import (
    SQLAlchemyOpeningBalanceRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.inventory.helpers import (
    build_opening_balance_actors,
    movement_totals,
)

OCCURRED_AT = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def make_line(
    quantity: str = "10",
    unit_cost: str = "450",
    lot_code: str | None = None,
    expires_at: date | None = None,
) -> OpeningBalanceLine:
    return OpeningBalanceLine.create(
        nomenclature_id=uuid4(),
        quantity=Decimal(quantity),
        unit_cost=Decimal(unit_cost),
        lot_code=lot_code,
        expires_at=expires_at,
    )


def make_opening_balance(
    lines: list[OpeningBalanceLine] | None = None,
) -> OpeningBalance:
    return OpeningBalance.create(
        org_unit_id=uuid4(),
        occurred_at=get_datetime_utc(),
        comment="Старт учёта",
        lines=lines if lines is not None else [make_line()],
    )


def test_new_opening_balance_is_draft() -> None:
    document = make_opening_balance()

    assert document.status is DocumentStatus.DRAFT
    assert document.is_draft is True
    assert document.posted_at is None
    assert document.comment == "Старт учёта"


def test_line_computes_total_cost_and_keeps_lot() -> None:
    expires_at = date(2027, 1, 15)
    line = OpeningBalanceLine.create(
        nomenclature_id=make_line().nomenclature_id,
        quantity=Decimal("2.5"),
        unit_cost=Decimal("199.90"),
        lot_code="L-001",
        expires_at=expires_at,
    )

    assert line.total_cost.kopecks == 49975
    assert line.lot_code == "L-001"
    assert line.expires_at == expires_at
    assert line.lot_id is None


def test_document_total_cost_sums_lines() -> None:
    document = make_opening_balance(
        [make_line("10", "450"), make_line("5", "480")]
    )

    assert document.total_cost.kopecks == 450000 + 240000


def test_post_marks_document_posted() -> None:
    document = make_opening_balance()

    document.post()

    assert document.status is DocumentStatus.POSTED
    assert document.posted_at is not None


def test_second_post_is_rejected() -> None:
    document = make_opening_balance()
    document.post()

    with pytest.raises(DocumentAlreadyPostedError):
        document.post()


def test_post_without_lines_is_rejected() -> None:
    document = make_opening_balance(lines=[])

    with pytest.raises(EmptyDocumentError):
        document.post()


def test_line_rejects_non_positive_quantity() -> None:
    with pytest.raises(EmptyMovementError):
        make_line(quantity="0")

    with pytest.raises(EmptyMovementError):
        make_line(quantity="-1")


def test_line_rejects_negative_cost() -> None:
    with pytest.raises(NegativeCostError):
        make_line(unit_cost="-1")


def test_revise_replaces_lines_and_comment() -> None:
    document = make_opening_balance([make_line("10", "450")])

    document.revise(
        occurred_at=datetime(2026, 11, 2, 10, 0, tzinfo=UTC),
        comment="Уточнили",
        lines=[make_line("3", "100")],
    )

    assert document.comment == "Уточнили"
    assert [line.quantity for line in document.lines] == [Decimal(3)]



@pytest.mark.db
async def test_create_assigns_opening_balance_number(
    db_session: AsyncSession, make_location
) -> None:
    location = await make_location()
    actors = build_opening_balance_actors(db_session)

    document_id = await actors.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            comment="Старт",
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=uuid4(),
                    quantity=Decimal(10),
                    unit_cost=Decimal(450),
                )
            ],
        )
    )

    stored = await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(
        document_id
    )

    assert stored is not None
    assert stored.number is not None
    assert stored.number.startswith("ВО-2026-")
    assert stored.status is DocumentStatus.DRAFT


@pytest.mark.db
async def test_post_adds_balance_lot_and_movement(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    actors = build_opening_balance_actors(db_session)

    expires_at = date(2027, 3, 1)
    document_id = await actors.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal("450.50"),
                    lot_code="START-001",
                    expires_at=expires_at,
                )
            ],
        )
    )

    await actors.post(PostOpeningBalanceCommand(opening_balance_id=document_id))

    stored = await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(
        document_id
    )
    assert stored is not None
    assert stored.status is DocumentStatus.POSTED
    assert stored.lines[0].lot_id is not None

    balance = (
        await db_session.execute(
            text(
                "select quantity, average_unit_cost, total_value"
                " from inventory.stock_balances"
                " where org_unit_id = :org_unit_id"
                " and nomenclature_id = :nomenclature_id"
            ),
            {"org_unit_id": location.id, "nomenclature_id": nomenclature.id},
        )
    ).one()
    assert balance.quantity == Decimal(10)
    assert balance.average_unit_cost == Decimal("450.5")
    assert balance.total_value == 450500

    lot_balance = (
        await db_session.execute(
            text(
                "select quantity, average_unit_cost, total_value"
                " from inventory.stock_lot_balances"
                " where org_unit_id = :org_unit_id"
                " and nomenclature_id = :nomenclature_id"
            ),
            {"org_unit_id": location.id, "nomenclature_id": nomenclature.id},
        )
    ).one()
    assert lot_balance.quantity == Decimal(10)
    assert lot_balance.average_unit_cost == Decimal("450.5")
    assert lot_balance.total_value == 450500

    movement_type = await db_session.scalar(
        text(
            "select movement_type from inventory.stock_movements"
            " where org_unit_id = :org_unit_id"
            " and nomenclature_id = :nomenclature_id"
        ),
        {"org_unit_id": location.id, "nomenclature_id": nomenclature.id},
    )
    assert movement_type == "opening_balance"

    quantity, cost = await movement_totals(
        db_session, location.id, nomenclature.id
    )
    assert quantity == Decimal(10)
    assert cost == 450500


@pytest.mark.db
async def test_opening_balance_journal_counts_lines_and_sums_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    first = await make_nomenclature(name="Говядина", sku="PYTEST-OB-BEEF")
    second = await make_nomenclature(name="Свинина", sku="PYTEST-OB-PORK")
    actors = build_opening_balance_actors(db_session)

    document_id = await actors.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            comment="Перенос с бумаги",
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=first.id,
                    quantity=Decimal("40.5"),
                    unit_cost=Decimal("450.5"),
                ),
                OpeningBalanceLineCommand(
                    nomenclature_id=second.id,
                    quantity=Decimal(18),
                    unit_cost=Decimal(610),
                ),
            ],
        )
    )

    items, total = await SQLAlchemyOpeningBalanceReader(db_session).list(
        org_unit_ids=[location.id]
    )

    assert total == 1
    assert items[0].id == document_id
    assert items[0].line_count == 2
    assert items[0].total_kopecks == 1824525 + 1098000
    assert items[0].comment == "Перенос с бумаги"
    assert items[0].number is not None

    detail = await SQLAlchemyOpeningBalanceReader(db_session).get(document_id)
    assert detail is not None
    assert detail.lines[0].unit_cost == Decimal("450.5")
    assert detail.lines[0].total_kopecks == 1824525
    assert detail.lines[1].total_kopecks == 1098000


@pytest.mark.db
async def test_update_draft_replaces_lines_and_comment(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    actors = build_opening_balance_actors(db_session)

    document_id = await actors.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            comment="Старый",
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(450),
                )
            ],
        )
    )

    await actors.update(
        UpdateOpeningBalanceCommand(
            opening_balance_id=document_id,
            occurred_at=OCCURRED_AT,
            comment="Новый",
            lines=[
                UpdateOpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(4),
                    unit_cost=Decimal(100),
                    lot_code="L-NEW",
                )
            ],
        )
    )

    stored = await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(
        document_id
    )
    assert stored is not None
    assert stored.comment == "Новый"
    assert [line.quantity for line in stored.lines] == [Decimal(4)]
    assert stored.lines[0].lot_code == "L-NEW"


@pytest.mark.db
async def test_update_after_post_is_rejected(
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
                    quantity=Decimal(1),
                    unit_cost=Decimal(10),
                )
            ],
        )
    )
    await actors.post(PostOpeningBalanceCommand(opening_balance_id=document_id))

    with pytest.raises(DocumentAlreadyPostedError):
        await actors.update(
            UpdateOpeningBalanceCommand(
                opening_balance_id=document_id,
                occurred_at=OCCURRED_AT,
                lines=[
                    UpdateOpeningBalanceLineCommand(
                        nomenclature_id=nomenclature.id,
                        quantity=Decimal(2),
                        unit_cost=Decimal(20),
                    )
                ],
            )
        )


@pytest.mark.db
async def test_delete_draft_removes_document_and_lines(
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
                    quantity=Decimal(2),
                    unit_cost=Decimal(50),
                )
            ],
        )
    )

    await actors.delete(
        DeleteOpeningBalanceCommand(opening_balance_id=document_id)
    )

    assert (
        await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(document_id)
        is None
    )
    lines = await db_session.scalar(
        text(
            "select count(*) from inventory.opening_balance_lines"
            " where opening_balance_id = :id"
        ),
        {"id": document_id},
    )
    assert lines == 0

    with pytest.raises(OpeningBalanceNotFoundError):
        await actors.delete(
            DeleteOpeningBalanceCommand(opening_balance_id=document_id)
        )


@pytest.mark.db
async def test_create_and_post_require_permission(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature()
    denied = build_opening_balance_actors(db_session, allowed=False)

    with pytest.raises(ForbiddenError):
        await denied.create(
            CreateOpeningBalanceCommand(
                org_unit_id=location.id,
                occurred_at=OCCURRED_AT,
                lines=[
                    OpeningBalanceLineCommand(
                        nomenclature_id=nomenclature.id,
                        quantity=Decimal(1),
                        unit_cost=Decimal(10),
                    )
                ],
            )
        )

    allowed = build_opening_balance_actors(db_session)
    document_id = await allowed.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OCCURRED_AT,
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                    unit_cost=Decimal(10),
                )
            ],
        )
    )

    with pytest.raises(ForbiddenError):
        await denied.post(
            PostOpeningBalanceCommand(opening_balance_id=document_id)
        )

    stored = await SQLAlchemyOpeningBalanceRepository(db_session).get_by_id(
        document_id
    )
    assert stored is not None
    assert stored.status is DocumentStatus.DRAFT
