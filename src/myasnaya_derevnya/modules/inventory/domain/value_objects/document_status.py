from enum import StrEnum


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"  # фаза 2
