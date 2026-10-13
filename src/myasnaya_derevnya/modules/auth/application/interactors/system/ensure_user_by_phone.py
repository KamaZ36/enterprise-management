from uuid import UUID

from myasnaya_derevnya.modules.auth.application.errors import InvalidPhoneNumber
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.domain.phone_number import normalize_phone_number
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)


class EnsureUserByPhoneInteractor:
    def __init__(
        self,
        user_repository: UserRepository,
        identity_repository: UserIdentityRepository,
    ) -> None:
        self._user_repository = user_repository
        self._identity_repository = identity_repository

    async def __call__(self, phone: str) -> UUID:
        identifier = normalize_phone_number(phone)

        if identifier is None:
            raise InvalidPhoneNumber()

        identity = await self._identity_repository.get_by_identifier_and_type(
            identifier=identifier, identity_type=UserIdentityType.PHONE_NUMBER
        )

        if identity is not None:
            return identity.user_id

        user = User.create()
        await self._user_repository.add(user)
        await self._identity_repository.add(
            UserIdentity.create(
                user_id=user.id,
                identity_type=UserIdentityType.PHONE_NUMBER,
                identifier=identifier,
            )
        )

        return user.id
