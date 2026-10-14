from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, DomainError, NotFoundError


class ProductionDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка правил производства"


class TechCardNotFoundError(NotFoundError):
    def __init__(self, tech_card_id: UUID) -> None:
        self._tech_card_id = tech_card_id

    def __str__(self) -> str:
        return f"Техкарта {self._tech_card_id} не найдена."


class ProductionWarehouseNotFoundError(NotFoundError):
    def __init__(self, warehouse_id: UUID) -> None:
        self._warehouse_id = warehouse_id

    def __str__(self) -> str:
        return f"Склад цеха {self._warehouse_id} не найден."


class ProductionOrderNotFoundError(NotFoundError):
    def __init__(self, order_id: UUID) -> None:
        self._order_id = order_id

    def __str__(self) -> str:
        return f"Производственное задание {self._order_id} не найдено."


class ProductionOrderLineNotFoundError(NotFoundError):
    def __init__(self, line_id: UUID) -> None:
        self._line_id = line_id

    def __str__(self) -> str:
        return f"Строка производственного задания {self._line_id} не найдена."


class InvalidTechCardLineError(ProductionDomainError):
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return f"Некорректная строка техкарты: {self._reason}"


class EmptyTechCardError(ProductionDomainError):
    def __str__(self) -> str:
        return "В техкарте должны быть хотя бы один вход и хотя бы один выход."


class MainOutputRequiredError(ProductionDomainError):
    def __str__(self) -> str:
        return "В техкарте с нормой по выходу должен быть ровно один основной продукт."


class EmptyBatchError(ProductionDomainError):
    def __str__(self) -> str:
        return "Количество закладок должно быть больше нуля."


class EmptyProductionOutputError(ProductionDomainError):
    def __str__(self) -> str:
        return "Нельзя провести задание без выпуска."


class EmptyProductionInputError(ProductionDomainError):
    def __str__(self) -> str:
        return "Нельзя провести задание без списания компонентов."


class OutputExceedsInputError(ProductionDomainError):
    def __str__(self) -> str:
        return "Выпуск больше входа: проверьте фактические количества."


class CostAllocationError(ProductionDomainError):
    def __str__(self) -> str:
        return "Сумма долей выпуска равна нулю: себестоимость разложить нечем."


class ProductionOrderNotDraftError(ConflictError):
    def __str__(self) -> str:
        return "Изменить можно только черновик производственного задания."
