from datetime import date

from myasnaya_derevnya.core.settings.base import BaseAppSettings


class OfdSettings(BaseAppSettings):
    """Параметры интеграции с ОФД.

    ``ofd_api_token`` пустой по умолчанию: без него синхронизация чеков
    недоступна, но приложение продолжает работать.
    """

    ofd_api_url: str = "https://ofd.ru/api/integration/v2"
    ofd_api_token: str = ""
    ofd_inn: str = ""
    # Время в чеке ОФД приходит без часового пояса. Считаем его местным
    # временем кассы и переводим в UTC для складских документов.
    ofd_timezone: str = "Europe/Moscow"
    ofd_request_timeout: float = 30.0
    # Чеки раньше этой даты не загружаем: до перехода склад не велся.
    ofd_cutover_date: date | None = None
