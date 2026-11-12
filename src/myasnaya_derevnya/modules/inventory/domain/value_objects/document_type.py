from enum import StrEnum


class DocumentType(StrEnum):
    RECEIPT = "receipt"
    WRITE_OFF = "write_off"
    SHIPMENT = "shipment"
    TRANSFER = "transfer"
    INVENTORY_COUNT = "inventory_count"
    OPENING_BALANCE = "opening_balance"
    PRODUCTION = "production"
    SALE = "sale"
