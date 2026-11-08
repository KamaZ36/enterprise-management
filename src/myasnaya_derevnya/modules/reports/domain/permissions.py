from myasnaya_derevnya.core.types.permission import Permission

READ_REPORTS = Permission(
    code="report.read",
    description="Просмотр отчётов по продажам, складу и производству",
)

ALL: tuple[Permission, ...] = (READ_REPORTS,)
