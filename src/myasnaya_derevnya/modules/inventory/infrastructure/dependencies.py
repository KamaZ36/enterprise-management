from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.interactors.create_location import (
    CreateLocationInteractor,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.location.base import (
    LocationRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.location.sqlalchemy import (
    SQLAlchemyLocationRepository,
)


class InventoryDepProvider(Provider):
    # REPOSITORIES

    @provide(scope=Scope.REQUEST)
    def get_location_repository(self, session: AsyncSession) -> LocationRepository:
        return SQLAlchemyLocationRepository(session)

    # INTERACTORS

    create_location_interactor = provide(CreateLocationInteractor, scope=Scope.REQUEST)
