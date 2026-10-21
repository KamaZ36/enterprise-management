from sqlalchemy import text

from myasnaya_derevnya.core.database.connection import async_session_maker

TEST_PREFIX = "PYTEST-"

INVENTORY_TABLES = (
    "inventory.stock_movements",
    "inventory.stock_postings",
    "inventory.inventory_count_lines",
    "inventory.inventory_counts",
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

# Уборка идёт от «детей» к «родителям»: связи с on delete restrict
# (документ → справочник, сотрудник → подразделение) не дадут удалить
# родителя первым. Системные строки (корневое подразделение, SUPER_ADMIN,
# администратор) тесты не создают, поэтому их не трогаем.
_CLEANUP_STATEMENTS = (
    # производственные задания ссылаются на техкарты и подразделения
    """
    delete from production.production_orders
     where tech_card_id in
           (select id from production.tech_cards where code like :prefix)
        or org_unit_id in
           (select id from business.org_units where code like :prefix)
    """,
    "delete from production.tech_cards where code like :prefix",
    # привязки прайс-листов ссылаются на прайс-листы
    """
    delete from catalog.price_list_bindings
     where price_list_id in
           (select id from catalog.price_lists where name like :prefix)
    """,
    "delete from catalog.price_lists where name like :prefix",
    "delete from catalog.nomenclatures where sku like :prefix",
    "delete from catalog.categories where name like :prefix",
    # кассы и их привязки создают только тесты
    """
    delete from fiscal.cash_register_bindings
     where cash_register_id in
           (select id from fiscal.cash_registers where name like :prefix)
    """,
    "delete from fiscal.cash_registers where name like :prefix",
    # клиентов и сотрудников создают только тесты
    "delete from customer.customers",
    "delete from staff.employees",
    """
    delete from staff.role_assignments
     where org_unit_id in
           (select id from business.org_units where code like :prefix)
    """,
    """
    delete from staff.role_assignments
     where role_id in
           (select id from staff.roles where code like :prefix)
    """,
    "delete from staff.roles where code like :prefix",
    """
    delete from business.companies
     where org_unit_id in
           (select id from business.org_units where code like :prefix)
    """,
    "delete from business.org_units where code like :prefix",
    # сессии и одноразовые коды нужны только внутри отдельного теста
    "delete from auth.one_time_codes",
    "delete from auth.user_sessions",
)


async def clean_database() -> None:
    async with async_session_maker() as session:
        await session.execute(text(f"TRUNCATE {', '.join(INVENTORY_TABLES)} CASCADE"))

        for statement in _CLEANUP_STATEMENTS:
            await session.execute(text(statement), {"prefix": f"{TEST_PREFIX}%"})

        await session.commit()
