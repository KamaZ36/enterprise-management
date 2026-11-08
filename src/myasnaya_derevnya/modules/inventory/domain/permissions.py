from myasnaya_derevnya.core.types.permission import Permission

CREATE_DOCUMENT = Permission(
    code="inventory.document.create",
    description="Создание складских документов",
)

POST_DOCUMENT = Permission(
    code="inventory.document.post",
    description="Проведение складских документов",
)

MANAGE_OPENING_BALANCE = Permission(
    code="inventory.opening_balance.manage",
    description="Ввод начальных остатков",
)


READ_BALANCES = Permission(
    code="inventory.balance.read",
    description="Просмотр остатков",
)

READ_COSTS = Permission(
    code="inventory.cost.read",
    description="Просмотр себестоимости",
)

READ_DOCUMENTS = Permission(
    code="inventory.document.read", description="Просмотр документов склада"
)

ALL: tuple[Permission, ...] = (
    CREATE_DOCUMENT,
    POST_DOCUMENT,
    MANAGE_OPENING_BALANCE,
    READ_BALANCES,
    READ_COSTS,
    READ_DOCUMENTS,
)
