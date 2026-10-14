from myasnaya_derevnya.core.types.permission import Permission

MANAGE_WAREHOUSES = Permission(
    code="inventory.warehouse.manage",
    description="Управление складами",
)

READ_WAREHOUSES = Permission(
    code="inventory.warehouse.read",
    description="Просмотр складов",
)


CREATE_DOCUMENT = Permission(
    code="inventory.document.create",
    description="Создание складских документов",
)

POST_DOCUMENT = Permission(
    code="inventory.document.post",
    description="Проведение складских документов",
)


READ_BALANCES = Permission(
    code="inventory.balance.read",
    description="Просмотр остатков",
)

READ_COSTS = Permission(
    code="inventory.cost.read",
    description="Просмотр себестоимости",
)

ALL: tuple[Permission, ...] = (
    MANAGE_WAREHOUSES,
    READ_WAREHOUSES,
    CREATE_DOCUMENT,
    POST_DOCUMENT,
    READ_BALANCES,
    READ_COSTS,
)


READ_DOCUMENTS = Permission(
    code="inventory.document.read", description="Просмотр документов склада"
)
