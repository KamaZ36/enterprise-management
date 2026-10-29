from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class PosAgentStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    PAUSED = "paused"


class PosAgent:
    """Установленный на кассе агент сбора продаж."""

    def __init__(
        self,
        id: UUID,
        source_id: UUID,
        install_id: str | None,
        api_key_hash: str,
        api_key_prefix: str,
        hostname: str | None,
        version: str | None,
        status: PosAgentStatus,
        pending_receipts: int,
        last_seen_at: datetime | None,
        last_success_at: datetime | None,
        last_error: str | None,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._source_id = source_id
        self._install_id = install_id
        self._api_key_hash = api_key_hash
        self._api_key_prefix = api_key_prefix
        self._hostname = hostname
        self._version = version
        self._status = status
        self._pending_receipts = pending_receipts
        self._last_seen_at = last_seen_at
        self._last_success_at = last_success_at
        self._last_error = last_error
        self._is_active = is_active
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        *,
        source_id: UUID,
        api_key_hash: str,
        api_key_prefix: str,
        install_id: str | None = None,
        hostname: str | None = None,
        version: str | None = None,
    ) -> PosAgent:
        now = get_datetime_utc()

        return cls(
            id=uuid7(),
            source_id=source_id,
            install_id=_optional_text(install_id, 64),
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            hostname=_optional_text(hostname, 255),
            version=_optional_text(version, 32),
            status=PosAgentStatus.OK,
            pending_receipts=0,
            last_seen_at=None,
            last_success_at=None,
            last_error=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def source_id(self) -> UUID:
        return self._source_id

    @property
    def install_id(self) -> str | None:
        return self._install_id

    @property
    def api_key_hash(self) -> str:
        return self._api_key_hash

    @property
    def api_key_prefix(self) -> str:
        return self._api_key_prefix

    @property
    def hostname(self) -> str | None:
        return self._hostname

    @property
    def version(self) -> str | None:
        return self._version

    @property
    def status(self) -> PosAgentStatus:
        return self._status

    @property
    def pending_receipts(self) -> int:
        return self._pending_receipts

    @property
    def last_seen_at(self) -> datetime | None:
        return self._last_seen_at

    @property
    def last_success_at(self) -> datetime | None:
        return self._last_success_at

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def bind_install(self, install_id: str) -> None:
        if self._install_id is None:
            self._install_id = _optional_text(install_id, 64)
            self._updated_at = get_datetime_utc()

    def rotate_key(self, *, api_key_hash: str, api_key_prefix: str) -> None:
        self._api_key_hash = api_key_hash
        self._api_key_prefix = api_key_prefix
        self._updated_at = get_datetime_utc()

    def set_active(self, is_active: bool) -> None:
        self._is_active = is_active
        self._updated_at = get_datetime_utc()

    def mark_seen(
        self,
        *,
        hostname: str | None = None,
        version: str | None = None,
    ) -> None:
        self._last_seen_at = get_datetime_utc()
        if hostname:
            self._hostname = _optional_text(hostname, 255)
        if version:
            self._version = _optional_text(version, 32)
        self._updated_at = get_datetime_utc()

    def mark_heartbeat(
        self,
        *,
        status: str,
        pending_receipts: int,
        last_success_at: datetime | None,
        last_error: str | None,
        hostname: str | None = None,
        version: str | None = None,
    ) -> None:
        self._status = _parse_status(status)
        self._pending_receipts = max(0, pending_receipts)
        if last_success_at is not None:
            self._last_success_at = last_success_at
        self._last_error = _truncate(last_error, 1024)
        self.mark_seen(hostname=hostname, version=version)

    def mark_sync_success(self, *, last_success_at: datetime) -> None:
        self._last_success_at = last_success_at
        self._last_error = None
        self._status = PosAgentStatus.OK
        self._updated_at = get_datetime_utc()

    def mark_sync_error(self, error: str) -> None:
        self._last_error = _truncate(error, 1024)
        self._status = PosAgentStatus.ERROR
        self._updated_at = get_datetime_utc()


def _parse_status(value: str) -> PosAgentStatus:
    try:
        return PosAgentStatus(value)
    except ValueError:
        return PosAgentStatus.WARNING


def _optional_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized[:limit]


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None

    return value[:limit]
