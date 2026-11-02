from myasnaya_derevnya.core.types.permission import Permission

READ_DOCUMENTS = Permission(
    code="veterinary.document.read",
    description="Просмотр ветеринарных документов",
)

ALL: tuple[Permission, ...] = (READ_DOCUMENTS,)
