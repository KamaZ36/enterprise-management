from enum import StrEnum
from uuid import UUID, uuid7


class UserCredentialType(StrEnum):
    PASSWORD = "password"


class UserCredential:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        credential_type: UserCredentialType,
        secret: str,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._credential_type = credential_type
        self._secret = secret

    @classmethod
    def create(
        cls, user_id: UUID, credential_type: UserCredentialType, secret: str
    ) -> UserCredential:
        return cls(
            id=uuid7(),
            user_id=user_id,
            credential_type=credential_type,
            secret=secret,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def credential_type(self) -> UserCredentialType:
        return self._credential_type

    @property
    def secret(self) -> str:
        return self._secret
