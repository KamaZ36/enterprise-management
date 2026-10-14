from myasnaya_derevnya.core.types.permission import Permission

CREATE_NOMENCLATURE = Permission(
    code="nomenclature.create", description="Создание номенклатуры"
)

READ_NOMENCLATURE = Permission(
    code="nomenclature.read", description="Просмотр номенклатуры"
)

UPDATE_NOMENCLATURE = Permission(
    code="nomenclature.update", description="Изменение номенклатуры"
)


CREATE_CATEGORY = Permission(code="category.create", description="Создание категории")

READ_CATEGORY = Permission(code="category.read", description="Просмотр категорий")

UPDATE_CATEGORY = Permission(code="category.update", description="Изменение категории")


CREATE_PRICE_LIST = Permission(
    code="price_list.create", description="Создание прайс-листа"
)

READ_PRICE_LIST = Permission(
    code="price_list.read", description="Просмотр прайс-листов"
)


CREATE_PRICE = Permission(
    code="price.create", description="Создание цены на номенклатуру"
)

READ_PRICE = Permission(code="price.read", description="Просмотр цен")


UPLOAD_IMAGE = Permission(code="image.upload", description="Загрузка изображений")
