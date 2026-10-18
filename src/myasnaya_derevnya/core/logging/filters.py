import logging

from myasnaya_derevnya.core.logging.context import get_request_id, get_user_id


class ContextFilter(logging.Filter):
    """Приклеивает к записи данные текущего запроса.

    Стоит на хендлере (см. ``setup_logging``), поэтому вызывающему коду не нужно
    передавать контекст через ``extra=`` в каждом вызове логгера: ``request_id``
    и ``user_id`` проставляются автоматически и доступны форматтеру.

    Пустые значения не пишутся вовсе, чтобы не засорять вывод ``None``-ами.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        if request_id:
            record.request_id = request_id

        user_id = get_user_id()
        if user_id:
            record.user_id = str(user_id)

        return True
