from myasnaya_derevnya.core.types.permission import Permission

MANAGE_EMPLOYEES = Permission(
    code="staff.employee.manage",
    description="Управление сотрудниками",
)

READ_EMPLOYEES = Permission(
    code="staff.employee.read",
    description="Просмотр сотрудников",
)

MANAGE_ROLES = Permission(
    code="staff.role.manage",
    description="Управление ролями",
)

READ_ROLES = Permission(
    code="staff.role.read",
    description="Просмотр ролей",
)

ASSIGN_ROLES = Permission(
    code="staff.role.assign",
    description="Назначение ролей",
)

READ_ORG = Permission(
    code="staff.org.read",
    description="Просмотр оргструктуры",
)

MANAGE_ORG = Permission(
    code="staff.org.manage",
    description="Управление оргструктурой",
)

MANAGE_GRANT_RULES = Permission(
    code="staff.grant_rules.manage",
    description="Управление матрицей выдачи ролей",
)

ALL: tuple[Permission, ...] = (
    MANAGE_EMPLOYEES,
    READ_EMPLOYEES,
    MANAGE_ROLES,
    READ_ROLES,
    ASSIGN_ROLES,
    READ_ORG,
    MANAGE_ORG,
    MANAGE_GRANT_RULES,
)
