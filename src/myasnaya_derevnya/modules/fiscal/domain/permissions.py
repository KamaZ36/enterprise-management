from myasnaya_derevnya.core.types.permission import Permission

CASH_REGISTER_READ = Permission(
    code="cash_register.read", description="Просмотр касс"
)

CASH_REGISTER_MANAGE = Permission(
    code="cash_register.manage", description="Управление кассами и привязками"
)

CASH_REGISTER_RECEIPT_READ = Permission(
    code="cash_register.receipt_read", description="Просмотр чеков ОФД"
)

CASH_REGISTER_RECEIPT_MANAGE = Permission(
    code="cash_register.receipt_manage",
    description="Сопоставление и проведение чеков ОФД",
)

CASH_REGISTER_RECEIPT_SYNC = Permission(
    code="cash_register.receipt_sync", description="Синхронизация чеков с ОФД"
)
