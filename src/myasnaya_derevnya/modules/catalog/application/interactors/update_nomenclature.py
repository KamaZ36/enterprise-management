from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import (
    CategoryNotFound,
    NomenclatureNotFound,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import UPDATE_NOMENCLATURE
from myasnaya_derevnya.modules.catalog.domain.services.nomenclature_changes import (
    NomenclatureChangesPolicy,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.base import (
    CategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class UpdateNomenclatureCommand:
    nomenclature_id: UUID
    name: str | None = None
    category_id: UUID | None = None
    unit: UnitOfMeasurement | None = None
    type_: NomenclatureType | None = None
    is_active: bool | None = None

    image_url: str | None = None
    description: str | None = None


class UpdateNomenclatureInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        nomenclature_repository: NomenclatureRepository,
        category_repository: CategoryRepository,
        movement_repository: StockMovementRepository,
        changes_policy: NomenclatureChangesPolicy,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._nomenclature_repository = nomenclature_repository
        self._category_repository = category_repository
        self._movement_repository = movement_repository
        self._changes_policy = changes_policy
        self._business_api = business_api
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateNomenclatureCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=current_user_id,
            permission=UPDATE_NOMENCLATURE,
        )
        if not allowed:
            raise ForbiddenError()

        nomenclature = await self._nomenclature_repository.get_by_id(
            command.nomenclature_id
        )
        if nomenclature is None:
            raise NomenclatureNotFound(command.nomenclature_id)

        if command.category_id is not None and not (
            await self._category_repository.check_exists_by_id(command.category_id)
        ):
            raise CategoryNotFound(command.category_id)

        if command.unit is not None or command.type_ is not None:
            has_movements = (
                await self._movement_repository.count_for_nomenclature(
                    command.nomenclature_id
                )
                > 0
            )
            self._changes_policy.ensure_changeable(
                nomenclature_id=nomenclature.id,
                current_unit=nomenclature.unit,
                new_unit=command.unit,
                current_type=nomenclature.type_,
                new_type=command.type_,
                has_movements=has_movements,
            )

        if command.name is not None:
            nomenclature.rename(command.name)
        if command.category_id is not None:
            nomenclature.change_category(command.category_id)
        if command.unit is not None:
            nomenclature.change_unit(command.unit)
        if command.type_ is not None:
            nomenclature.change_type(command.type_)
        if command.is_active is not None:
            nomenclature.activate() if command.is_active else nomenclature.deactivate()
        if command.image_url is not None:
            nomenclature.change_image_url(command.image_url)
        if command.description is not None:
            nomenclature.change_description(command.description)

        await self._nomenclature_repository.save(nomenclature)
        await self._transaction_manager.commit()
