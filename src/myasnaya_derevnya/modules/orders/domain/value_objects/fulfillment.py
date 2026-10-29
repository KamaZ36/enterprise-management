from enum import StrEnum


class FulfillmentType(StrEnum):
    """Способ получения заказа.

    ``DELIVERY`` пока не доступен в UI (доставка — в разработке), но значение
    хранится заранее, чтобы включить доставку без миграции данных.
    """

    PICKUP = "pickup"
    DELIVERY = "delivery"
