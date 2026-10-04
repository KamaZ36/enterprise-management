from uuid import UUID

from myasnaya_derevnya.modules.auth.application.interactors.create import (
    CreateUserInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.create_employee_credential import (
    CreateEmployeeCredentialCommand,
    CreateEmployeeCredentialInteractor,
)


class AuthAPI:
    def __init__(
        self,
        create_user_interactor: CreateUserInteractor,
        create_employee_credential_interactor: CreateEmployeeCredentialInteractor,
    ) -> None:
        self._create_user_interactor = create_user_interactor
        self._create_employee_credential_interactor = (
            create_employee_credential_interactor
        )

    async def create_user(self) -> UUID:
        user_id = await self._create_user_interactor()
        return user_id

    async def create_employee_credential(
        self, user_id: UUID, password: str, username: str
    ) -> None:
        command = CreateEmployeeCredentialCommand(
            user_id=user_id, password=password, username=username
        )
        await self._create_employee_credential_interactor(command)
