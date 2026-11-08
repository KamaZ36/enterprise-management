from dataclasses import dataclass

from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)

PREFIX_BY_TYPE = {
    DocumentType.RECEIPT: "ПН",
    DocumentType.WRITE_OFF: "СП",
    DocumentType.TRANSFER: "ПМ",
    DocumentType.INVENTORY_COUNT: "ИНВ",
    DocumentType.OPENING_BALANCE: "ВО",
}


@dataclass(frozen=True, slots=True)
class DocumentNumber:
    """Человекочитаемый номер документа: ``ПН-2026-000123``."""

    value: str

    @classmethod
    def create(
        cls,
        document_type: DocumentType,
        year: int,
        sequence: int,
    ) -> DocumentNumber:
        prefix = PREFIX_BY_TYPE[document_type]

        return cls(value=f"{prefix}-{year}-{sequence:06d}")
