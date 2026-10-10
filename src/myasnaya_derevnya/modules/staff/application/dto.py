from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RoleListItem:
    """Строка справочника ролей: уровень и признаки для назначения."""

    id: UUID
    code: str
    name: str
    level: int
    is_system: bool
    is_assignable: bool
    is_wildcard: bool
