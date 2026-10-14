from enum import StrEnum


class LossKind(StrEnum):
    SHRINKAGE = "shrinkage"
    COOKING = "cooking"
    TRIMMING = "trimming"
    DEFROST = "defrost"
    DEFECT = "defect"
