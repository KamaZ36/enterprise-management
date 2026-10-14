from myasnaya_derevnya.core.types.permission import Permission


def all_permissions() -> tuple[Permission, ...]:
    from myasnaya_derevnya.modules.auth.domain import permissions as auth
    from myasnaya_derevnya.modules.business.domain import permissions as business
    from myasnaya_derevnya.modules.catalog.domain import permissions as catalog
    from myasnaya_derevnya.modules.customer.domain import permissions as customer
    from myasnaya_derevnya.modules.inventory.domain import permissions as inventory
    from myasnaya_derevnya.modules.sales.domain import permissions as sales
    from myasnaya_derevnya.modules.staff.domain import permissions as staff

    modules = (auth, business, catalog, customer, inventory, sales, staff)
    found = [
        value
        for module in modules
        for value in vars(module).values()
        if isinstance(value, Permission)
    ]

    return tuple(sorted(found, key=lambda permission: permission.code))
