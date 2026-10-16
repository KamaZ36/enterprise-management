from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import CategoryNotFound
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_NOMENCLATURE
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateNomenclatureCommand:
    sku: str
    name: str
    unit: UnitOfMeasurement
    category_id: UUID
    image_url: str | None = None
    description: str | None = None


class CreateNomenclatureInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        nomenclature_repository: NomenclatureRepository,
        category_repository: CategoryRepository,
        transaction_manager: TransactionManager,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._nomenclature_repository = nomenclature_repository
        self._category_repository = category_repository
        self._transaction_manager = transaction_manager
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, command: CreateNomenclatureCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        if not await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=CREATE_NOMENCLATURE,
        ):
            raise ForbiddenError()

        if not await self._category_repository.check_exists_by_id(command.category_id):
            raise CategoryNotFound(command.category_id)

        nomenclature = Nomenclature.create(
            sku=command.sku,
            name=command.name,
            unit=command.unit,
            category_id=command.category_id,
            image_url=command.image_url,
            description=command.description,
        )

        await self._nomenclature_repository.add(nomenclature)
        await self._transaction_manager.commit()

        return nomenclature.id
