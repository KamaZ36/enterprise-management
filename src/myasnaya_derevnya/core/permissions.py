from myasnaya_derevnya.core.types.permission import Permission


def all_permissions() -> tuple[Permission, ...]:
    from myasnaya_derevnya.modules.auth.domain import permissions as auth
    from myasnaya_derevnya.modules.business.domain import permissions as business
    from myasnaya_derevnya.modules.catalog.domain import permissions as catalog
    from myasnaya_derevnya.modules.customer.domain import permissions as customer
    from myasnaya_derevnya.modules.fiscal.domain import permissions as fiscal
    from myasnaya_derevnya.modules.inventory.domain import permissions as inventory
    from myasnaya_derevnya.modules.orders.domain import permissions as orders
    from myasnaya_derevnya.modules.pos.domain import permissions as pos
    from myasnaya_derevnya.modules.production.domain import permissions as production
    from myasnaya_derevnya.modules.staff.domain import permissions as staff

    modules = (
        auth,
        business,
        catalog,
        customer,
        fiscal,
        inventory,
        production,
        orders,
        pos,
        staff,
    )
    found = [
        value
        for module in modules
        for value in vars(module).values()
        if isinstance(value, Permission)
    ]

    return tuple(sorted(found, key=lambda permission: permission.code))
