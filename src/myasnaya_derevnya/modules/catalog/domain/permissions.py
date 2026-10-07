from myasnaya_derevnya.core.types.permission import Permission

# NOMENCLATURES

CREATE_NOMENCLATURE = Permission(
    code="nomenclature.create", description="Создание номенклатуры"
)


# CATEGORIES
CREATE_CATEGORY = Permission(code="category.create", description="Создание категории")


# PRICE LISTS
CREATE_PRICE_LIST = Permission(
    code="price_list.create", description="Создание прайс-листа"
)

# PRICES
CREATE_PRICE = Permission(
    code="price.create", description="Создание цены на номенклатуру"
)
