from myasnaya_derevnya.core.types.permission import Permission

CASH_REGISTER_READ = Permission(
    code="cash_register.read", description="Просмотр касс"
)

CASH_REGISTER_MANAGE = Permission(
    code="cash_register.manage", description="Управление кассами и привязками"
)
