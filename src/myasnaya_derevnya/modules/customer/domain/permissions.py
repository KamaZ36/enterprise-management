from myasnaya_derevnya.core.types.permission import Permission

# CUSTOMERS
READ_CUSTOMERS = Permission(
    code="customer.read", description="Просмотр профилей клиентов"
)

UPDATE_CUSTOMER = Permission(
    code="customer.update", description="Изменение профиля клиента"
)
