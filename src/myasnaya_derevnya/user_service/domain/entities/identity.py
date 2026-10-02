from enum import StrEnum
from uuid import UUID, uuid7


class UserIdentityProviderType(StrEnum):
    PASSWORD = "password"  # Для сотрудников (логин + хэш пароля)
    PHONE_OTP = "phone_otp"


class Identity:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        provider: UserIdentityProviderType,
        identifier: str,
        password_hash: str | None,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._provider = provider
        self._identifier = identifier
        self._password_hash = password_hash

    @classmethod
    def create_password_identity(
        cls, user_id: UUID, username: str, password_hash: str
    ) -> Identity:
        """Фабричный метод для создания логина/пароля сотрудника."""
        return cls(
            id=uuid7(),
            user_id=user_id,
            provider=UserIdentityProviderType.PASSWORD,
            identifier=username,
            password_hash=password_hash,
        )

    @classmethod
    def create_phone_identity(cls, user_id: UUID, phone: str) -> Identity:
        """Фабричный метод для создания OTP-входа клиента по телефону."""
        return cls(
            id=uuid7(),
            user_id=user_id,
            provider=UserIdentityProviderType.PHONE_OTP,
            identifier=phone,
            password_hash=None,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def provider(self) -> UserIdentityProviderType:
        return self._provider

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def password_hash(self) -> str | None:
        return self._password_hash

    def update_password(self, new_password_hash: str) -> None:
        """Смена пароля сотрудника."""
        if self._provider != UserIdentityProviderType.PASSWORD:
            raise ValueError("Нельзя установить пароль для этого способа авторизации")
        self._password_hash = new_password_hash
