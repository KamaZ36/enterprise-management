from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.domain.entities.location import (
    Location,
    LocationType,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import MANAGE_LOCATION
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.location.base import (
    LocationRepository,
)


@dataclass(frozen=True, slots=True)
class CreateLocationCommand:
    name: str
    location_type: LocationType
    address: str


class CreateLocationInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        location_repository: LocationRepository,
        access_service: AccessService,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._location_repository = location_repository
        self._access_service = access_service
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateLocationCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        await self._access_service.require(
            user_id=current_user_id, permission=MANAGE_LOCATION, location_id=None
        )

        location = Location.create(
            name=command.name,
            location_type=command.location_type,
            address=command.address,
        )

        await self._location_repository.add(location)
        await self._transaction_manager.commit()

        return location.id
