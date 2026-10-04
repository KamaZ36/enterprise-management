from myasnaya_derevnya.core.types.permission import Permission

MANAGE_EMPLOYEES = Permission(
    code="employee:manage", description="Управление сотрудниками"
)

MANAGE_ROLES = Permission(
    "employee_roles:manage", description="Управление ролями сотрудников"
)
