from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)


class CatalogAPI:
    """Публичный интерфейс модуля catalog для других модулей.

    Наружу отдаются простые данные, а не доменные типы каталога: складскому
    модулю нужен только код типа номенклатуры, чтобы проверить совместимость
    со складом.
    """

    def __init__(self, nomenclature_repository: NomenclatureRepository) -> None:
        self._nomenclature_repository = nomenclature_repository

    async def nomenclature_types(
        self, nomenclature_ids: Iterable[UUID]
    ) -> dict[UUID, str]:
        return await self._nomenclature_repository.get_types(set(nomenclature_ids))
