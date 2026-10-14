from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class OrderAccess:
    """Кто вправе действовать с заказом.

    Сотрудник — по праву на точку заказа. Клиент — только если заказ его.
    Профиль читается, но не создаётся: иначе сотруднику завёлся бы лишний.
    """

    def __init__(self, staff_api: StaffAPI, customer_api: CustomerAPI) -> None:
        self._staff_api = staff_api
        self._customer_api = customer_api

    async def is_staff(
        self, *, user_id: UUID, org_unit_id: UUID, permission: Permission
    ) -> bool:
        return await self._staff_api.can(
            user_id=user_id, permission=permission, org_unit_id=org_unit_id
        )

    async def ensure_can_act(
        self, *, user_id: UUID, order: Order, permission: Permission
    ) -> None:
        if await self.is_staff(
            user_id=user_id, org_unit_id=order.org_unit_id, permission=permission
        ):
            return

        own_customer_id = await self._customer_api.get_customer_id(user_id)

        if own_customer_id is None or order.customer_id != own_customer_id:
            raise ForbiddenError()

    async def customer_id_of(self, user_id: UUID) -> UUID | None:
        """Профиль клиента, если он есть. Ничего не создаёт."""
        return await self._customer_api.get_customer_id(user_id)

    async def ensure_can_view(
        self,
        *,
        user_id: UUID,
        org_unit_id: UUID,
        customer_id: UUID | None,
        permission: Permission,
    ) -> None:
        """Просмотр готовых данных, где нет сущности заказа под рукой."""
        if await self.is_staff(
            user_id=user_id, org_unit_id=org_unit_id, permission=permission
        ):
            return

        own_customer_id = await self._customer_api.get_customer_id(user_id)

        if own_customer_id is None or customer_id != own_customer_id:
            raise ForbiddenError()
