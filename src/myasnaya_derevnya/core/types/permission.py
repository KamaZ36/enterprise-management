from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Permission:
    code: str
    description: str
