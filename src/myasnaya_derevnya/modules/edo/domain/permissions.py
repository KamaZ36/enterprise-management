from myasnaya_derevnya.core.types.permission import Permission

READ_DOCUMENTS = Permission(
    code="edo.document.read",
    description="Просмотр входящих документов ЭДО",
)

MANAGE_DOCUMENTS = Permission(
    code="edo.document.manage",
    description="Регистрация входящих документов ЭДО",
)

ALL: tuple[Permission, ...] = (READ_DOCUMENTS, MANAGE_DOCUMENTS)
