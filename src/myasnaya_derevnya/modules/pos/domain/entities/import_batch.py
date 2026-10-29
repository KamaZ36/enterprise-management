from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class PosImportBatch:
    """Один загруженный агентом файл журнала продаж DoKa."""

    def __init__(
        self,
        id: UUID,
        source_id: UUID,
        agent_id: UUID | None,
        file_name: str,
        file_sha256: str | None,
        exported_at: datetime | None,
        received_at: datetime,
        receipts_total: int,
        receipts_created: int,
        receipts_duplicate: int,
        receipts_posted: int,
        receipts_pending: int,
        receipts_failed: int,
        status: str,
        error: str | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._source_id = source_id
        self._agent_id = agent_id
        self._file_name = file_name
        self._file_sha256 = file_sha256
        self._exported_at = exported_at
        self._received_at = received_at
        self._receipts_total = receipts_total
        self._receipts_created = receipts_created
        self._receipts_duplicate = receipts_duplicate
        self._receipts_posted = receipts_posted
        self._receipts_pending = receipts_pending
        self._receipts_failed = receipts_failed
        self._status = status
        self._error = error
        self._created_at = created_at

    @classmethod
    def start(
        cls,
        *,
        source_id: UUID,
        agent_id: UUID | None,
        file_name: str,
        file_sha256: str | None,
        exported_at: datetime | None,
        receipts_total: int,
    ) -> PosImportBatch:
        now = get_datetime_utc()

        return cls(
            id=uuid7(),
            source_id=source_id,
            agent_id=agent_id,
            file_name=file_name,
            file_sha256=file_sha256,
            exported_at=exported_at,
            received_at=now,
            receipts_total=receipts_total,
            receipts_created=0,
            receipts_duplicate=0,
            receipts_posted=0,
            receipts_pending=0,
            receipts_failed=0,
            status="received",
            error=None,
            created_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def source_id(self) -> UUID:
        return self._source_id

    @property
    def agent_id(self) -> UUID | None:
        return self._agent_id

    @property
    def file_name(self) -> str:
        return self._file_name

    @property
    def file_sha256(self) -> str | None:
        return self._file_sha256

    @property
    def exported_at(self) -> datetime | None:
        return self._exported_at

    @property
    def received_at(self) -> datetime:
        return self._received_at

    @property
    def receipts_total(self) -> int:
        return self._receipts_total

    @property
    def receipts_created(self) -> int:
        return self._receipts_created

    @property
    def receipts_duplicate(self) -> int:
        return self._receipts_duplicate

    @property
    def receipts_posted(self) -> int:
        return self._receipts_posted

    @property
    def receipts_pending(self) -> int:
        return self._receipts_pending

    @property
    def receipts_failed(self) -> int:
        return self._receipts_failed

    @property
    def status(self) -> str:
        return self._status

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def count_created(self) -> None:
        self._receipts_created += 1

    def count_duplicate(self) -> None:
        self._receipts_duplicate += 1

    def count_posted(self) -> None:
        self._receipts_posted += 1

    def count_pending(self) -> None:
        self._receipts_pending += 1

    def count_failed(self) -> None:
        self._receipts_failed += 1

    def finish(self, *, error: str | None = None) -> None:
        self._status = "failed" if error else "completed"
        self._error = error[:1024] if error else None
