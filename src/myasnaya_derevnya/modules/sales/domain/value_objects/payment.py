from enum import StrEnum


class PaymentMethod(StrEnum):
    """Способ оплаты заказа.

    ``ONLINE`` пока не используется в витрине (онлайн-оплата — в разработке),
    но значение хранится заранее, чтобы включить оплату без миграции данных.
    """

    ONLINE = "online"
    ON_PICKUP = "on_pickup"
    ON_DELIVERY = "on_delivery"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
