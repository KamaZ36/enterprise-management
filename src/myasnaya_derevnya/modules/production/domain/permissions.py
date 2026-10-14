from myasnaya_derevnya.core.types.permission import Permission

READ_TECH_CARDS = Permission(
    code="production.tech_card.read",
    description="Просмотр техкарт",
)

MANAGE_TECH_CARDS = Permission(
    code="production.tech_card.manage",
    description="Создание техкарт и новых редакций",
)


READ_ORDERS = Permission(
    code="production.order.read",
    description="Просмотр производственных заданий",
)

MANAGE_ORDERS = Permission(
    code="production.order.manage",
    description="Создание, правка и отмена производственных заданий",
)

POST_ORDER = Permission(
    code="production.order.post",
    description="Проведение производственных заданий",
)


ALL: tuple[Permission, ...] = (
    READ_TECH_CARDS,
    MANAGE_TECH_CARDS,
    READ_ORDERS,
    MANAGE_ORDERS,
    POST_ORDER,
)
