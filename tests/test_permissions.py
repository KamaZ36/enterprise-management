from myasnaya_derevnya.core.permissions import all_permissions


def test_every_permission_has_a_unique_code_and_description() -> None:
    permissions = all_permissions()

    assert permissions
    codes = [permission.code for permission in permissions]
    assert len(codes) == len(set(codes))
    assert all(permission.code for permission in permissions)
    assert all(permission.description for permission in permissions)


EXPECTED_NAMESPACES = {
    "cash_register",
    "category",
    "customer",
    "image",
    "inventory",
    "nomenclature",
    "order",
    "org_unit",
    "price",
    "price_list",
    "production",
    "staff",
}


def test_registry_is_sorted_and_covers_every_namespace() -> None:
    permissions = all_permissions()

    codes = [permission.code for permission in permissions]
    assert codes == sorted(codes)

    namespaces = {code.split(".", 1)[0] for code in codes}

    assert namespaces == EXPECTED_NAMESPACES


def test_registry_matches_permissions_declared_in_modules() -> None:
    from myasnaya_derevnya.core.types.permission import Permission
    from myasnaya_derevnya.modules.business.domain import permissions as business
    from myasnaya_derevnya.modules.catalog.domain import permissions as catalog
    from myasnaya_derevnya.modules.customer.domain import permissions as customer
    from myasnaya_derevnya.modules.fiscal.domain import permissions as fiscal
    from myasnaya_derevnya.modules.inventory.domain import permissions as inventory
    from myasnaya_derevnya.modules.orders.domain import permissions as orders
    from myasnaya_derevnya.modules.production.domain import permissions as production
    from myasnaya_derevnya.modules.staff.domain import permissions as staff

    declared = [
        value.code
        for module in (
            business,
            catalog,
            customer,
            fiscal,
            inventory,
            production,
            orders,
            staff,
        )
        for value in vars(module).values()
        if isinstance(value, Permission)
    ]

    assert sorted(declared) == [permission.code for permission in all_permissions()]
