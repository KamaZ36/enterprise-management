from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)


class RoleAssignmentRepository(ABC):
    @abstractmethod
    async def add(self, assignment: RoleAssignment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, assignment: RoleAssignment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, assignment_id: UUID) -> RoleAssignment | None:
        raise NotImplementedError

    @abstractmethod
    async def load_active_for_user(
        self,
        user_id: UUID,
    ) -> list[ResolvedAssignment]:
        raise NotImplementedError
