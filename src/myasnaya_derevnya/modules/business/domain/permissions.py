# ORG UNIT

from myasnaya_derevnya.core.types.permission import Permission

ORG_UNIT_CREATE = Permission(
    code="org_unit.create", description="Создание организационной единицы"
)

ORG_UNIT_READ = Permission(
    code="org_unit.read", description="Просмотр организационной структуры"
)
