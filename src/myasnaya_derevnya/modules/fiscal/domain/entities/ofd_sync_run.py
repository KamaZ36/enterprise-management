from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class OfdSyncRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class OfdSyncRun:
    """Журнал выгрузки чеков из ОФД: что и когда запрашивали."""

    def __init__(
        self,
        id: UUID,
        inn: str,
        reg_number: str,
        period_from: datetime,
        period_to: datetime,
        started_at: datetime,
        finished_at: datetime | None,
        status: OfdSyncRunStatus,
        receipts_found: int,
        receipts_created: int,
        error: str | None,
    ) -> None:
        self._id = id
        self._inn = inn
        self._reg_number = reg_number
        self._period_from = period_from
        self._period_to = period_to
        self._started_at = started_at
        self._finished_at = finished_at
        self._status = status
        self._receipts_found = receipts_found
        self._receipts_created = receipts_created
        self._error = error

    @classmethod
    def start(
        cls,
        *,
        inn: str,
        reg_number: str,
        period_from: datetime,
        period_to: datetime,
    ) -> OfdSyncRun:
        return cls(
            id=uuid7(),
            inn=inn,
            reg_number=reg_number,
            period_from=period_from,
            period_to=period_to,
            started_at=get_datetime_utc(),
            finished_at=None,
            status=OfdSyncRunStatus.RUNNING,
            receipts_found=0,
            receipts_created=0,
            error=None,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def inn(self) -> str:
        return self._inn

    @property
    def reg_number(self) -> str:
        return self._reg_number

    @property
    def period_from(self) -> datetime:
        return self._period_from

    @property
    def period_to(self) -> datetime:
        return self._period_to

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def finished_at(self) -> datetime | None:
        return self._finished_at

    @property
    def status(self) -> OfdSyncRunStatus:
        return self._status

    @property
    def receipts_found(self) -> int:
        return self._receipts_found

    @property
    def receipts_created(self) -> int:
        return self._receipts_created

    @property
    def error(self) -> str | None:
        return self._error

    def succeed(self, *, found: int, created: int) -> None:
        self._status = OfdSyncRunStatus.SUCCESS
        self._receipts_found = found
        self._receipts_created = created
        self._finished_at = get_datetime_utc()
        self._error = None

    def fail(self, error: str, *, found: int = 0, created: int = 0) -> None:
        self._status = OfdSyncRunStatus.FAILED
        self._receipts_found = found
        self._receipts_created = created
        self._finished_at = get_datetime_utc()
        self._error = error[:1024]
