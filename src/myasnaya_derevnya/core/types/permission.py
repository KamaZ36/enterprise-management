from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class Permission:
    """Право доступа"""

    code: str
    description: str = ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Permission):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)
