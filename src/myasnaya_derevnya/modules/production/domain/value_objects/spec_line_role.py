from enum import StrEnum


class SpecLineRole(StrEnum):
    COMPONENT = "component"
    OUTPUT = "output"
    LOSS = "loss"


class OutputKind(StrEnum):
    MAIN = "main"
    BY_PRODUCT = "by_product"
