from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.create import (
    CreateOpeningBalanceCommand,
    OpeningBalanceLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.opening_balances.post import (
    PostOpeningBalanceCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffCommand,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.sqlalchemy import (
    SQLAlchemyReportsReader,
)
from tests.modules.inventory.helpers import (
    build_interactors,
    build_opening_balance_actors,
)

pytestmark = pytest.mark.db

OPENING_AT = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
PERIOD_AT = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)


async def test_turnover_counts_opening_inbound_and_outbound(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    nomenclature = await make_nomenclature(name="Говядина", sku="BEEF")

    opening = build_opening_balance_actors(db_session)
    opening_id = await opening.create(
        CreateOpeningBalanceCommand(
            org_unit_id=location.id,
            occurred_at=OPENING_AT,
            lines=[
                OpeningBalanceLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )
    await opening.post(
        PostOpeningBalanceCommand(opening_balance_id=opening_id)
    )

    actors = build_interactors(db_session)
    receipt_id = await actors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=PERIOD_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(5),
                    unit_cost=Decimal(200),
                )
            ],
        )
    )
    await actors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    write_off_id = await actors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=location.id,
            occurred_at=PERIOD_AT,
            reason="Порча",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(3),
                )
            ],
        )
    )
    await actors.post_write_off(
        PostWriteOffCommand(write_off_id=write_off_id)
    )

    rows = await SQLAlchemyReportsReader(db_session).turnover(
        date_from=datetime(2026, 11, 5).date(),
        date_to=datetime(2026, 11, 30).date(),
        org_unit_ids=[location.id],
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.nomenclature_name == "Говядина"
    assert row.sku == "BEEF"
    assert row.opening_quantity == Decimal(10)
    assert row.inbound_quantity == Decimal(5)
    assert row.outbound_quantity == Decimal(3)
    assert row.closing_quantity == Decimal(12)
    assert row.opening_value_kopecks == 100000
    assert row.inbound_value_kopecks == 100000
    assert row.outbound_value_kopecks == 40000
    assert row.closing_value_kopecks == 160000


async def test_turnover_filters_by_search(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    location = await make_location()
    beef = await make_nomenclature(name="Говядина", sku="BEEF")
    pork = await make_nomenclature(name="Свинина", sku="PORK")

    actors = build_interactors(db_session)
    receipt_id = await actors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=location.id,
            occurred_at=PERIOD_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=beef.id,
                    quantity=Decimal(5),
                    unit_cost=Decimal(100),
                ),
                ReceiptLineCommand(
                    nomenclature_id=pork.id,
                    quantity=Decimal(7),
                    unit_cost=Decimal(200),
                ),
            ],
        )
    )
    await actors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    reader = SQLAlchemyReportsReader(db_session)
    rows = await reader.turnover(
        date_from=datetime(2026, 11, 8).date(),
        date_to=datetime(2026, 11, 8).date(),
        org_unit_ids=[location.id],
        search="Говядина",
    )

    assert [row.nomenclature_name for row in rows] == ["Говядина"]
