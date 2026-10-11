from enum import StrEnum


class DocumentType(StrEnum):
    RECEIPT = "receipt"
    WRITE_OFF = "write_off"
    TRANSFER = "transfer"
    INVENTORY_COUNT = "inventory_count"
    PRODUCTION = "production"
