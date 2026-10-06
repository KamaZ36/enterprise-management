from dataclasses import dataclass

from myasnaya_derevnya.core.errors import DomainError


@dataclass(frozen=True, slots=True, eq=False)
class InventoryDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка модуля Inventory"


@dataclass(frozen=True, slots=True, eq=False)
class EmptyLocationNameError(InventoryDomainError):
    def __str__(self) -> str:
        return "Название локации бизнеса не может быть пустым"


@dataclass(frozen=True, slots=True, eq=False)
class EmptyWarehouseNameError(InventoryDomainError):
    def __str__(self) -> str:
        return "Название склада не может быть пустым"
