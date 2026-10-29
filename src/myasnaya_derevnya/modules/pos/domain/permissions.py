from myasnaya_derevnya.core.types.permission import Permission

POS_SOURCE_READ = Permission(
    code="pos.source_read", description="Просмотр источников продаж DoKa"
)

POS_SOURCE_MANAGE = Permission(
    code="pos.source_manage",
    description="Управление источниками DoKa и ключами агентов",
)

POS_RECEIPT_READ = Permission(
    code="pos.receipt_read", description="Просмотр чеков DoKa"
)

POS_RECEIPT_MANAGE = Permission(
    code="pos.receipt_manage",
    description="Сопоставление и проведение чеков DoKa",
)
