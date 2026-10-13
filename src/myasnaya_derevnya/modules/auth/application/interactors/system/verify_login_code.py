from myasnaya_derevnya.modules.auth.application.errors import (
    InvalidPhoneNumber,
    LoginCodeAttemptsExceeded,
    LoginCodeExpired,
    LoginCodeInvalid,
    LoginCodeNotFound,
)
from myasnaya_derevnya.modules.auth.application.services.login_code_service import (
    LoginCodeService,
)
from myasnaya_derevnya.modules.auth.domain.phone_number import normalize_phone_number
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.base import (
    OneTimeCodeRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc


class VerifyLoginCodeInteractor:
    def __init__(
        self,
        code_repository: OneTimeCodeRepository,
        login_code_service: LoginCodeService,
    ) -> None:
        self._code_repository = code_repository
        self._login_code_service = login_code_service

    async def __call__(self, phone: str, code: str) -> None:
        identifier = normalize_phone_number(phone)

        if identifier is None:
            raise InvalidPhoneNumber()

        one_time_code = await self._code_repository.get_latest_by_identifier(identifier)

        if one_time_code is None:
            raise LoginCodeNotFound()

        if one_time_code.is_expired(get_datetime_utc()):
            await self._code_repository.delete_by_identifier(identifier)
            raise LoginCodeExpired()

        if one_time_code.attempts_exhausted:
            raise LoginCodeAttemptsExceeded()

        if not one_time_code.matches(self._login_code_service.hash(identifier, code)):
            one_time_code.register_failed_attempt()
            await self._code_repository.update(one_time_code)
            raise LoginCodeInvalid()

        await self._code_repository.delete_by_identifier(identifier)
