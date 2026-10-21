from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.fiscal.domain.errors import (
    InvalidBindingPeriodError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class CashRegisterBinding:
    """Привязка кассы к подразделению на период.

    Период полуоткрытый: ``[effective_from, effective_to)``.
    ``effective_to is None`` — привязка действует до сих пор.
    """

    def __init__(
        self,
        id: UUID,
        cash_register_id: UUID,
        org_unit_id: UUID,
        effective_from: datetime,
        effective_to: datetime | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._cash_register_id = cash_register_id
        self._org_unit_id = org_unit_id
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        *,
        cash_register_id: UUID,
        org_unit_id: UUID,
        effective_from: datetime,
    ) -> CashRegisterBinding:
        if effective_from.tzinfo is None:
            raise TimezoneRequiredError()

        return cls(
            id=uuid7(),
            cash_register_id=cash_register_id,
            org_unit_id=org_unit_id,
            effective_from=effective_from,
            effective_to=None,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def cash_register_id(self) -> UUID:
        return self._cash_register_id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def effective_from(self) -> datetime:
        return self._effective_from

    @property
    def effective_to(self) -> datetime | None:
        return self._effective_to

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_open(self) -> bool:
        return self._effective_to is None

    def is_active_at(self, at: datetime) -> bool:
        return self._effective_from <= at and (
            self._effective_to is None or at < self._effective_to
        )

    def close(self, effective_to: datetime) -> None:
        if effective_to.tzinfo is None:
            raise TimezoneRequiredError()

        if effective_to <= self._effective_from:
            raise InvalidBindingPeriodError()

        self._effective_to = effective_to
