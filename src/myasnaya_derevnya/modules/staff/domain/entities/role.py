from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class Role:
    def __init__(
        self,
        id_: UUID,
        name: str,
        code: str,
        description: str | None,
        level: int,
        is_system: bool,
        is_assignable: bool,
        is_wildcard: bool,
        permission_codes: frozenset[str],
        grantable_role_ids: frozenset[UUID],
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id_
        self._name = name
        self._code = code
        self._description = description
        self._level = level
        self._is_system = is_system
        self._is_assignable = is_assignable
        self._is_wildcard = is_wildcard
        self._permissions = permission_codes
        self._grantable_role_ids = grantable_role_ids
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        level: int,
        description: str | None,
        is_system: bool,
        is_assignable: bool,
        is_wildcard: bool = False,
    ) -> Role:
        return cls(
            id_=uuid7(),
            code=code,
            name=name,
            level=level,
            description=description,
            is_system=is_system,
            is_assignable=is_assignable,
            is_wildcard=is_wildcard,
            permission_codes=frozenset(),
            grantable_role_ids=frozenset(),
            created_at=get_datetime_utc(),
            updated_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @property
    def level(self) -> int:
        return self._level

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def permission_codes(self) -> frozenset[str]:
        return frozenset(self._permissions)

    @property
    def is_assignable(self) -> bool:
        return self._is_assignable

    @property
    def is_system(self) -> bool:
        return self._is_system

    @property
    def is_wildcard(self) -> bool:
        return self._is_wildcard

    @property
    def grantable_role_ids(self) -> frozenset[UUID]:
        return self._grantable_role_ids

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def created_at(self) -> datetime:
        return self._created_at
