from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class RoleAssignmentStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class RoleAssignment:
    def __init__(
        self,
        id_: UUID,
        user_id: UUID,
        role_id: UUID,
        org_unit_id: UUID | None,  # None = вся компания
        include_descendants: bool,
        status: RoleAssignmentStatus,
        granted_by: UUID | None,
        created_at: datetime,
    ) -> None:
        self._id = id_
        self._user_id = user_id
        self._role_id = role_id
        self._org_unit_id = org_unit_id
        self._include_descendants = include_descendants
        self._status = status
        self._granted_by = granted_by
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        user_id: UUID,
        role_id: UUID,
        org_unit_id: UUID | None,
        include_descendants: bool,
        granted_by: UUID,
    ) -> RoleAssignment:
        return cls(
            id_=uuid7(),
            user_id=user_id,
            role_id=role_id,
            org_unit_id=org_unit_id,
            include_descendants=include_descendants,
            status=RoleAssignmentStatus.ACTIVE,
            granted_by=granted_by,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def role_id(self) -> UUID:
        return self._role_id

    @property
    def org_unit_id(self) -> UUID | None:
        return self._org_unit_id

    @property
    def include_descendants(self) -> bool:
        return self._include_descendants

    @property
    def status(self) -> RoleAssignmentStatus:
        return self._status

    @property
    def granted_by(self) -> UUID | None:
        return self._granted_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_active(self) -> bool:
        return self._status is RoleAssignmentStatus.ACTIVE

    def revoke(self) -> None:
        self._status = RoleAssignmentStatus.REVOKED
