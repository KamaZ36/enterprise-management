from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, DomainError, NotFoundError


@dataclass(slots=True, eq=False)
class InventoryDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка складского учёта"


@dataclass(slots=True, eq=False)
class InsufficientStockError(InventoryDomainError):
    warehouse_id: UUID
    nomenclature_id: UUID
    available: Decimal
    requested: Decimal

    def __str__(self) -> str:
        return (
            f"Недостаточно остатка: доступно {self.available}, "
            f"запрошено {self.requested}"
        )


@dataclass(slots=True, eq=False)
class InsufficientLotStockError(InventoryDomainError):
    lot_id: UUID
    available: Decimal
    requested: Decimal

    def __str__(self) -> str:
        return (
            f"В партии недостаточно остатка: доступно {self.available}, "
            f"запрошено {self.requested}"
        )


@dataclass(slots=True, eq=False)
class EmptyMovementError(InventoryDomainError):
    def __str__(self) -> str:
        return "Количество движения не может быть нулевым"


@dataclass(slots=True, eq=False)
class NegativeCostError(InventoryDomainError):
    def __str__(self) -> str:
        return "Сумма не может быть отрицательной"


@dataclass(slots=True, eq=False)
class WarehouseNotFoundError(NotFoundError):
    warehouse_id: UUID

    def __str__(self) -> str:
        return f"Склад {self.warehouse_id} не найден"


@dataclass(slots=True, eq=False)
class ReceiptNotFoundError(NotFoundError):
    receipt_id: UUID

    def __str__(self) -> str:
        return f"Поступление {self.receipt_id} не найдено"


@dataclass(slots=True, eq=False)
class WriteOffNotFoundError(NotFoundError):
    write_off_id: UUID

    def __str__(self) -> str:
        return f"Списание {self.write_off_id} не найдено"


@dataclass(slots=True, eq=False)
class StockLotNotFoundError(NotFoundError):
    nomenclature_id: UUID
    lot_code: str

    def __str__(self) -> str:
        return f"Партия '{self.lot_code}' не найдена на складе"


@dataclass(slots=True, eq=False)
class NomenclatureNotFoundError(NotFoundError):
    nomenclature_id: UUID

    def __str__(self) -> str:
        return f"Номенклатура {self.nomenclature_id} не найдена"


@dataclass(slots=True, eq=False)
class OrgUnitNotFoundError(NotFoundError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return f"Организационная единица {self.org_unit_id} не найдена"


@dataclass(slots=True, eq=False)
class WarehouseCodeAlreadyExistsError(ConflictError):
    code: str

    def __str__(self) -> str:
        return f"Склад с кодом '{self.code}' уже существует"


@dataclass(slots=True, eq=False)
class WarehouseInactiveError(InventoryDomainError):
    warehouse_id: UUID

    def __str__(self) -> str:
        return f"Склад {self.warehouse_id} неактивен"


@dataclass(slots=True, eq=False)
class DocumentAlreadyPostedError(ConflictError):
    document_id: UUID

    def __str__(self) -> str:
        return f"Документ {self.document_id} уже проведён"


@dataclass(slots=True, eq=False)
class EmptyFieldError(InventoryDomainError):
    field: str

    def __str__(self) -> str:
        return f"Поле '{self.field}' не может быть пустым"


@dataclass(slots=True, eq=False)
class TimezoneRequiredError(InventoryDomainError):
    field: str

    def __str__(self) -> str:
        return f"Поле '{self.field}' должно содержать часовой пояс"


@dataclass(slots=True, eq=False)
class EmptyDocumentError(InventoryDomainError):
    document_id: UUID

    def __str__(self) -> str:
        return f"Документ {self.document_id} не содержит строк"


@dataclass(slots=True, eq=False)
class WarehouseInUseError(ConflictError):
    warehouse_id: UUID

    def __str__(self) -> str:
        return (
            f"Нельзя изменить назначение склада {self.warehouse_id}: "
            "на нём есть остатки"
        )


@dataclass(slots=True, eq=False)
class TransferNotFoundError(NotFoundError):
    transfer_id: UUID

    def __str__(self) -> str:
        return f"Перемещение {self.transfer_id} не найдено."


@dataclass(slots=True, eq=False)
class SameWarehouseTransferError(InventoryDomainError):
    warehouse_id: UUID

    def __str__(self) -> str:
        return "Нельзя переместить товар на тот же склад."
