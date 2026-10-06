from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)


class CreateNomenclatureInteractor:
    def __init__(
        self, identity_provider: IdentityProvider, access_serivce: AccessService
    ) -> None:
        self._identity_provider = identity_provider
        self._access_service = access_serivce
