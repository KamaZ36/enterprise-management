import logging

from myasnaya_derevnya.modules.auth.infrastructure.service.login_code_sender.base import (
    LoginCodeSender,
)

logger = logging.getLogger(__name__)


class LoggingLoginCodeSender(LoginCodeSender):
    """Отладочный отправитель: печатает код в лог только при ``DEBUG``.

    Без ``DEBUG`` кода в логе нет — иначе одноразовые коды утекали бы в логи.
    Боевой канал доставки (SMS/мессенджер) пока не реализован.
    """

    def __init__(self, debug: bool = False) -> None:
        self._debug = debug

    async def send(self, identifier: str, code: str) -> None:
        if self._debug:
            logger.warning("Код входа для %s: %s", identifier, code)
            return

        logger.error(
            "Канал доставки кодов не настроен; код для %s не отправлен", identifier
        )
