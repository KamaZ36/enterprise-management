from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import CREATE_NOMENCLATURE
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)


@dataclass(frozen=True, slots=True)
class CreateNomenclatureCommand:
    sku: str
    name: str
    unit: UnitOfMeasurement
    type_: NomenclatureType
    category_id: UUID


class CreateNomenclatureInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        nomenclature_repository: NomenclatureRepository,
        transaction_manager: TransactionManager,
        access_serivce: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._nomenclature_repository = nomenclature_repository
        self._transaction_manager = transaction_manager
        self._access_service = access_serivce

    async def __call__(self, command: CreateNomenclatureCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        org_unit_id_context = await self._identity_provider.get_current_org_unit_id()
        if not await self._access_service.can(
            user_id=current_user_id,
            permission=CREATE_NOMENCLATURE,
            org_unit_id=org_unit_id_context,
        ):
            raise ForbiddenError()

        nomenclature = Nomenclature.create(
            sku=command.sku,
            name=command.name,
            unit=command.unit,
            type_=command.type_,
            category_id=command.category_id,
        )

        await self._nomenclature_repository.add(nomenclature)
        await self._transaction_manager.commit()

        return nomenclature.id
