from enum import StrEnum


class DocumentType(StrEnum):
    """Тип документа для записи проведения.

    Проведение общее для всех типов, поэтому тип хранится строкой рядом с
    идентификатором документа.
    """

    RECEIPT = "receipt"
    WRITE_OFF = "write_off"
    TRANSFER = "transfer"  # фаза 2
    INVENTORY_COUNT = "inventory_count"  # фаза 2
    PRODUCTION = "production"  # фаза 3
