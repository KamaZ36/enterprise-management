from myasnaya_derevnya.core.types.permission import Permission

# ORDERS
CREATE_ORDER = Permission(code="order.create", description="Создание заказа")

READ_ORDERS = Permission(code="order.read", description="Просмотр заказов")

UPDATE_ORDER = Permission(code="order.update", description="Изменение заказа")

CANCEL_ORDER = Permission(code="order.cancel", description="Отмена заказа")
