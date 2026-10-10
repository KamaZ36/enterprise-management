from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, DomainError, NotFoundError


@dataclass(slots=True, eq=False)
class InventoryDomainError(DomainError):
    """Базовое нарушение бизнес-правил складского учёта"""

    def __str__(self) -> str:
        return "Ошибка складского учёта"


@dataclass(slots=True, eq=False)
class InsufficientStockError(InventoryDomainError):
    """Нельзя списать больше, чем есть на складе"""

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
    """Нельзя списать из партии больше, чем в ней есть"""

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
    """Проводка с нулевым количеством не имеет смысла"""

    def __str__(self) -> str:
        return "Количество движения не может быть нулевым"


@dataclass(slots=True, eq=False)
class NegativeCostError(InventoryDomainError):
    """Себестоимость не может быть отрицательной"""

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
    """Партия, на которую ссылается документ, не найдена."""

    nomenclature_id: UUID
    lot_code: str

    def __str__(self) -> str:
        return f"Партия '{self.lot_code}' не найдена на складе"


@dataclass(slots=True, eq=False)
class NomenclatureNotFoundError(NotFoundError):
    """Номенклатура из строки документа не найдена в каталоге"""

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
    """Нельзя двигать остатки по закрытому складу"""

    warehouse_id: UUID

    def __str__(self) -> str:
        return f"Склад {self.warehouse_id} неактивен"


@dataclass(slots=True, eq=False)
class DocumentAlreadyPostedError(ConflictError):
    """Повторное проведение документа запрещено"""

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
    """Даты учёта обязаны иметь часовой пояс."""

    field: str

    def __str__(self) -> str:
        return f"Поле '{self.field}' должно содержать часовой пояс"


@dataclass(slots=True, eq=False)
class EmptyDocumentError(InventoryDomainError):
    """Проводить документ без строк нельзя"""

    document_id: UUID

    def __str__(self) -> str:
        return f"Документ {self.document_id} не содержит строк"


@dataclass(slots=True, eq=False)
class NomenclatureNotAllowedInWarehouseError(InventoryDomainError):
    """Номенклатуру нельзя хранить на складе такого назначения"""

    warehouse_id: UUID
    nomenclature_id: UUID
    warehouse_type: str
    nomenclature_type: str

    def __str__(self) -> str:
        return (
            f"Номенклатура типа '{self.nomenclature_type}' не может храниться "
            f"на складе типа '{self.warehouse_type}'"
        )
