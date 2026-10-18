from uuid import UUID

from myasnaya_derevnya.modules.sales.application.dto import Cart, CartLine
from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.payment import (
    PaymentMethod,
    PaymentStatus,
)

# Оплата по самовывозу/доставке — на месте, онлайн-оплата появится позже.
PAYMENT_METHOD_BY_FULFILLMENT: dict[FulfillmentType, PaymentMethod] = {
    FulfillmentType.PICKUP: PaymentMethod.ON_PICKUP,
    FulfillmentType.DELIVERY: PaymentMethod.ON_DELIVERY,
}


def build_cart(order: Order | None, org_unit_id: UUID) -> Cart:
    if order is None:
        return Cart(
            org_unit_id=org_unit_id,
            fulfillment_type=FulfillmentType.PICKUP.value,
            payment_method=PaymentMethod.ON_PICKUP.value,
            payment_status=PaymentStatus.PENDING.value,
            comment=None,
            total=0,
            lines=[],
        )

    return Cart(
        id=order.id,
        org_unit_id=order.org_unit_id,
        fulfillment_type=order.fulfillment_type.value,
        payment_method=order.payment_method.value,
        payment_status=order.payment_status.value,
        comment=order.comment,
        total=order.total,
        lines=[
            CartLine(
                nomenclature_id=line.nomenclature_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                total=line.total,
            )
            for line in order.lines
        ],
    )
