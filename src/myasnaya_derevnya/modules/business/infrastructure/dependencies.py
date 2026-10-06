from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.sqlalchemy import (
    SQLAlchemyOrgUnitRepository,
)
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI


class BusinessDepProvider(Provider):
    # REPOSITORIES

    @provide(scope=Scope.REQUEST)
    def get_org_unit_repository(self, session: AsyncSession) -> OrgUnitRepository:
        return SQLAlchemyOrgUnitRepository(session)

    # OTHER

    @provide(scope=Scope.REQUEST)
    def get_business_api_facade(
        self, org_unit_repository: OrgUnitRepository
    ) -> BusinessAPI:
        return BusinessAPI(org_unit_repository=org_unit_repository)
