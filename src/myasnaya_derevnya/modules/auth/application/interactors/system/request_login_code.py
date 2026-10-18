import logging
from datetime import timedelta

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.application.errors import (
    InvalidPhoneNumber,
    LoginCodeHourlyLimitExceeded,
    LoginCodeRequestTooFrequent,
)
from myasnaya_derevnya.modules.auth.application.services.login_code_service import (
    LoginCodeService,
)
from myasnaya_derevnya.modules.auth.domain.entities.one_time_code import OneTimeCode
from myasnaya_derevnya.modules.auth.domain.phone_number import normalize_phone_number
from myasnaya_derevnya.modules.auth.infrastructure.repositories.one_time_code.base import (
    OneTimeCodeRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.base import (
    LoginCodeSender,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


class RequestLoginCodeInteractor:
    def __init__(
        self,
        code_repository: OneTimeCodeRepository,
        login_code_service: LoginCodeService,
        login_code_sender: LoginCodeSender,
        transaction_manager: TransactionManager,
    ) -> None:
        self._code_repository = code_repository
        self._login_code_service = login_code_service
        self._login_code_sender = login_code_sender
        self._transaction_manager = transaction_manager

    async def __call__(self, phone: str) -> None:
        identifier = normalize_phone_number(phone)

        if identifier is None:
            raise InvalidPhoneNumber()

        now = get_datetime_utc()
        latest = await self._code_repository.get_latest_by_identifier(identifier)

        if latest is not None:
            allowed_at = latest.created_at + self._login_code_service.min_interval
            wait_seconds = (allowed_at - now).total_seconds()

            if wait_seconds > 0:
                raise LoginCodeRequestTooFrequent(
                    retry_after_seconds=int(wait_seconds) + 1
                )

        sent_last_hour = await self._code_repository.count_created_since(
            identifier, now - timedelta(hours=1)
        )

        if sent_last_hour >= self._login_code_service.hourly_limit:
            raise LoginCodeHourlyLimitExceeded()

        code = self._login_code_service.generate()

        await self._code_repository.add(
            OneTimeCode.create(
                identifier=identifier,
                code_hash=self._login_code_service.hash(identifier, code),
                ttl=self._login_code_service.ttl,
                max_attempts=self._login_code_service.max_attempts,
            )
        )
        await self._transaction_manager.commit()
        await self._login_code_sender.send(identifier, code)

        logger.info("Запрошен код входа", extra={"identifier": identifier})
