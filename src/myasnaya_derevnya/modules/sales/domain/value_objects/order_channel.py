from enum import StrEnum


class OrderChannel(StrEnum):
    SITE = "site"
    POS = "pos"
    PHONE = "phone"
