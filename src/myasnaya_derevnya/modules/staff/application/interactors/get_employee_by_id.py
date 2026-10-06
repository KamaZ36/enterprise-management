from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class GetEmployeeByIdQuery:
    employee_id: UUID


class GetEmployeeByIdInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._access_service = access_service

    async def __call__(self, command: )