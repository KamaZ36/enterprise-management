from myasnaya_derevnya.core.types.permission import Permission

CREATE_EMPLOYEE = Permission(
    code="create_employee", description="Создать профиль сотрудника"
)

CREATE_CREDENTIAL_EMPLOYEE = Permission(
    code="create_credential_employee", description="Создать учетные данные сотруднику"
)
