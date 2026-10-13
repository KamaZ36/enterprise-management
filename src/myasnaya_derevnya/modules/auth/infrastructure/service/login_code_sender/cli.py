import logging

from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.base import (
    LoginCodeSender,
)

logger = logging.getLogger(__name__)


class LoggingLoginCodeSender(LoginCodeSender):
    async def send(self, identifier: str, code: str) -> None:
        logger.warning("Код входа для %s: %s", identifier, code)
