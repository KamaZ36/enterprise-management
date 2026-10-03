from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.organization.application.interactors.create_location import (
    CreateLocationInteractor,
)
from myasnaya_derevnya.modules.organization.infrastructure.location.base import (
    LocationRepository,
)
from myasnaya_derevnya.modules.organization.infrastructure.location.sqlalchemy import (
    SQLAlchemyLocationRepository,
)


class OrganizationDepProvidre(Provider):
    # REPOSITORIES

    @provide(scope=Scope.REQUEST)
    def get_location_repository(self, session: AsyncSession) -> LocationRepository:
        return SQLAlchemyLocationRepository(session)

    # INTERACTORS

    create_location_interactor = provide(CreateLocationInteractor, scope=Scope.REQUEST)
