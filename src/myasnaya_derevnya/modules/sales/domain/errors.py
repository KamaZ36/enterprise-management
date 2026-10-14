from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, DomainError, NotFoundError


class SalesDomainError(DomainError):
    """Нарушение правил заказа: вызывающий может исправить запрос."""

    def __str__(self) -> str:
        return "Ошибка правил заказа"


class TimezoneRequiredError(SalesDomainError):
    def __str__(self) -> str:
        return "Время должно быть с указанием часового пояса."


class EmptyOrderLineError(SalesDomainError):
    def __str__(self) -> str:
        return "Количество в позиции заказа должно быть больше нуля."


class NegativePriceError(SalesDomainError):
    def __str__(self) -> str:
        return "Цена в позиции заказа не может быть отрицательной."


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID) -> None:
        self._order_id = order_id

    def __str__(self) -> str:
        return f"Заказ {self._order_id} не найден."


class OrderIsNotDraftError(ConflictError):
    def __str__(self) -> str:
        return "Менять можно только черновик заказа."


class OrderStatusTransitionError(ConflictError):
    def __init__(self, current: str, target: str) -> None:
        self._current = current
        self._target = target

    def __str__(self) -> str:
        return f"Из статуса «{self._current}» нельзя перейти в «{self._target}»."


class OrderAlreadyClosedError(ConflictError):
    def __str__(self) -> str:
        return "Выданный или отменённый заказ изменить нельзя."


class NotSoldAtPointError(SalesDomainError):
    """Позиции нет в прайс-листе точки: продать её нельзя, и цену взять негде."""

    def __init__(self, nomenclature_id: UUID) -> None:
        self._nomenclature_id = nomenclature_id

    def __str__(self) -> str:
        return f"Позиция {self._nomenclature_id} не продаётся в этой точке."
