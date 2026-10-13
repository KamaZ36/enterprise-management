from uuid import UUID

from myasnaya_derevnya.modules.auth.application.interactors.system.create_employee_credential import (
    CreateEmployeeCredentialCommand,
    CreateEmployeeCredentialInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.create_user import (
    CreateUserInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.ensure_user_by_phone import (
    EnsureUserByPhoneInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.request_login_code import (
    RequestLoginCodeInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.reset_employee_password import (
    ResetEmployeePasswordCommand,
    ResetEmployeePasswordInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.start_session import (
    StartSessionInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.verify_login_code import (
    VerifyLoginCodeInteractor,
)


class AuthAPI:
    def __init__(
        self,
        create_user_interactor: CreateUserInteractor,
        create_employee_credential_interactor: CreateEmployeeCredentialInteractor,
        reset_employee_password_interactor: ResetEmployeePasswordInteractor,
        ensure_user_by_phone_interactor: EnsureUserByPhoneInteractor,
        request_login_code_interactor: RequestLoginCodeInteractor,
        verify_login_code_interactor: VerifyLoginCodeInteractor,
        start_session_interactor: StartSessionInteractor,
    ) -> None:
        self._create_user_interactor = create_user_interactor
        self._create_employee_credential_interactor = (
            create_employee_credential_interactor
        )
        self._reset_employee_password_interactor = reset_employee_password_interactor
        self._ensure_user_by_phone_interactor = ensure_user_by_phone_interactor
        self._request_login_code_interactor = request_login_code_interactor
        self._verify_login_code_interactor = verify_login_code_interactor
        self._start_session_interactor = start_session_interactor

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

    async def reset_employee_password(self, user_id: UUID, password: str) -> None:
        command = ResetEmployeePasswordCommand(user_id=user_id, password=password)

        await self._reset_employee_password_interactor(command)

    async def ensure_user_by_phone(self, phone: str) -> UUID:
        return await self._ensure_user_by_phone_interactor(phone)

    async def request_login_code(self, phone: str) -> None:
        await self._request_login_code_interactor(phone)

    async def verify_login_code(self, phone: str, code: str) -> None:
        await self._verify_login_code_interactor(phone, code)

    async def start_session(self, user_id: UUID) -> UUID:
        return await self._start_session_interactor(user_id)
