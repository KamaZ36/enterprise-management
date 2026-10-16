from sqlalchemy import text

from myasnaya_derevnya.core.database.connection import async_session_maker

TEST_PREFIX = "PYTEST-"

INVENTORY_TABLES = (
    "inventory.stock_movements",
    "inventory.stock_postings",
    "inventory.transfer_lines",
    "inventory.transfers",
    "inventory.receipt_lines",
    "inventory.receipts",
    "inventory.write_off_lines",
    "inventory.write_offs",
    "inventory.stock_lot_balances",
    "inventory.stock_lots",
    "inventory.stock_balances",
)


async def clean_database() -> None:
    async with async_session_maker() as session:
        await session.execute(text(f"TRUNCATE {', '.join(INVENTORY_TABLES)} CASCADE"))
        await session.execute(
            text("delete from catalog.nomenclatures where sku like :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.execute(
            text("delete from catalog.categories where name like :prefix"),
            {"prefix": f"{TEST_PREFIX}%"},
        )
        await session.commit()
