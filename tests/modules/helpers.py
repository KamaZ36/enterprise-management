"""Общее для интеграционных тестов модулей: маркеры данных и очистка базы."""

from sqlalchemy import text

from myasnaya_derevnya.core.database.connection import async_session_maker

TEST_PREFIX = "PYTEST-"

INVENTORY_TABLES = (
    "inventory.stock_movements",
    "inventory.stock_postings",
    "inventory.receipt_lines",
    "inventory.receipts",
    "inventory.write_off_lines",
    "inventory.write_offs",
    "inventory.stock_lot_balances",
    "inventory.stock_lots",
    "inventory.stock_balances",
    "inventory.warehouses",
)


async def clean_database() -> None:
    """Убирает за собой: складские таблицы целиком, каталожные — только свои.

    Каталожные строки помечены префиксом, потому что справочник может быть
    заполнен и вручную, а тесты не должны его затирать.
    """
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
