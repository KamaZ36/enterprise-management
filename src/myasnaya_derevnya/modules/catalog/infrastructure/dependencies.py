from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.application.interactors.create_category import (
    CreateCategoryInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_nomenclature import (
    CreateNomenclatureInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_price import (
    CreatePriceInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.create_price_list import (
    CreatePriceListInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_categories import (
    ListCategoriesInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_nomenclatures import (
    ListNomenclaturesInteractor,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.category.base import (
    CategoryReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.category.sqlalchemy import (
    SQLAlchemyCategoryReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature.base import (
    NomenclatureReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.sqlalchemy import (
    SQLAlchemyCategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.base import (
    PriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.sqlalchemy import (
    SQLAlchemyPriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.base import (
    PriceListRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.sqlalchemy import (
    SQLAlchemyPriceListRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI


class CatalogDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_nomenclature_repository(
        self, session: AsyncSession
    ) -> NomenclatureRepository:
        return SQLAlchemyNomenclatureRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_category_repository(self, session: AsyncSession) -> CategoryRepository:
        return SQLAlchemyCategoryRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_price_list_repository(self, session: AsyncSession) -> PriceListRepository:
        return SQLAlchemyPriceListRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_price_repository(self, session: AsyncSession) -> PriceRepository:
        return SQLAlchemyPriceRepository(session)

    # READERS

    @provide(scope=Scope.REQUEST)
    def get_nomenclature_reader(self, session: AsyncSession) -> NomenclatureReader:
        return SQLAlchemyNomenclatureReader(session)

    @provide(scope=Scope.REQUEST)
    def get_category_reader(self, session: AsyncSession) -> CategoryReader:
        return SQLAlchemyCategoryReader(session)

    # FACADE

    @provide(scope=Scope.REQUEST)
    def get_catalog_api(
        self, nomenclature_repository: NomenclatureRepository
    ) -> CatalogAPI:
        return CatalogAPI(nomenclature_repository=nomenclature_repository)

    # INTERACTOR

    create_nomenclature_interactor = provide(
        CreateNomenclatureInteractor, scope=Scope.REQUEST
    )
    list_nomenclatures_interactor = provide(
        ListNomenclaturesInteractor, scope=Scope.REQUEST
    )
    list_categories_interactor = provide(ListCategoriesInteractor, scope=Scope.REQUEST)
    create_category_interactor = provide(CreateCategoryInteractor, scope=Scope.REQUEST)
    create_price_list_interactor = provide(
        CreatePriceListInteractor, scope=Scope.REQUEST
    )
    create_price_interactor = provide(CreatePriceInteractor, scope=Scope.REQUEST)
