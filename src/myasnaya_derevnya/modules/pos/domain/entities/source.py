from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.pos.domain.errors import EmptyPosTextError
from myasnaya_derevnya.modules.pos.domain.value_objects.identifiers import (
    normalize_doka_org_id,
)
from myasnaya_derevnya.utils import get_datetime_utc


class PosSource:
    """Касса DoKa, привязанная к складской локации."""

    def __init__(
        self,
        id: UUID,
        doka_org_id: str,
        name: str,
        org_unit_id: UUID,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._doka_org_id = doka_org_id
        self._name = name
        self._org_unit_id = org_unit_id
        self._is_active = is_active
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        doka_org_id: str,
        name: str,
        org_unit_id: UUID,
    ) -> PosSource:
        now = get_datetime_utc()

        return cls(
            id=uuid7(),
            doka_org_id=normalize_doka_org_id(doka_org_id),
            name=_required_name(name),
            org_unit_id=org_unit_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def doka_org_id(self) -> str:
        return self._doka_org_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(
        self,
        *,
        name: str | None = None,
        org_unit_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> None:
        if name is not None:
            self._name = _required_name(name)
        if org_unit_id is not None:
            self._org_unit_id = org_unit_id
        if is_active is not None:
            self._is_active = is_active

        self._updated_at = get_datetime_utc()


def _required_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise EmptyPosTextError("name")

    return normalized
