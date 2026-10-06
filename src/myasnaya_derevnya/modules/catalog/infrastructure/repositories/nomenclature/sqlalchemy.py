from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import Nomenclature
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)


class SQLAlchemyNomenclatureRepository(NomenclatureRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, nomenclature: Nomenclature) -> None:
        stmt = insert()
