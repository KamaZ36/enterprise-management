from myasnaya_derevnya.core.types.permission import Permission

# NOMENCLATURES

CREATE_NOMENCLATURE = Permission(
    code="nomenclature.create", description="Создание номенклатуры"
)

READ_NOMENCLATURE = Permission(
    code="nomenclature.read", description="Просмотр номенклатуры"
)


# CATEGORIES

CREATE_CATEGORY = Permission(code="category.create", description="Создание категории")

READ_CATEGORY = Permission(code="category.read", description="Просмотр категорий")


# PRICE LISTS

CREATE_PRICE_LIST = Permission(
    code="price_list.create", description="Создание прайс-листа"
)

READ_PRICE_LIST = Permission(
    code="price_list.read", description="Просмотр прайс-листов"
)

# PRICES
CREATE_PRICE = Permission(
    code="price.create", description="Создание цены на номенклатуру"
)

READ_PRICE = Permission(code="price.read", description="Просмотр цен")
