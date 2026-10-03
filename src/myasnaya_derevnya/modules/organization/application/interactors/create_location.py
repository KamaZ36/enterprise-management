from dataclasses import dataclass

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.presentation.facade import AuthFacade
from myasnaya_derevnya.modules.organization.domain.entities.location import (
    Location,
    LocationType,
)
from myasnaya_derevnya.modules.organization.domain.permissions import LOCATIONS_MANAGE
from myasnaya_derevnya.modules.organization.infrastructure.location.base import (
    LocationRepository,
)


@dataclass(frozen=True, slots=True)
class CreateLocationCommand:
    location_type: LocationType
    name: str
    code: str
    address: str | None


class CreateLocationInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        location_repository: LocationRepository,
        transaction_manager: TransactionManager,
        auth_module: AuthFacade,
    ) -> None:
        self._identity_provider = identity_provider
        self._location_repository = location_repository
        self._transaction_manager = transaction_manager
        self._auth_module = auth_module

    async def __call__(self, command: CreateLocationCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        await self._auth_module.require(
            user_id=current_user_id, permission=LOCATIONS_MANAGE
        )

        location = Location.create(
            location_type=command.location_type,
            name=command.name,
            code=command.code,
            address=command.address,
        )

        await self._location_repository.add(location)
        await self._transaction_manager.commit()
