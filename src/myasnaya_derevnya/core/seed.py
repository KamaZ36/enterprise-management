import asyncio

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


async def bootstrap_system() -> None:
    print("=== Инициализация ===")

    username = settings.initial_admin_username
    password = settings.initial_admin_password
    role_code = settings.admin_role_code
    role_name = settings.admin_role_name

    async with container() as context:
        user_repository = await context.get(UserRepository)
        user_credential_repository = await context.get(CredentialRepository)
        user_identity_repository = await context.get(UserIdentityRepository)

        role_repository = await context.get(RoleRepository)
        role_assignment_repository = await context.get(RoleAssignmentRepository)

        transaction_manager = await context.get(TransactionManager)
        password_service = await context.get(PasswordService)

        user_identity = None
        role = None

        role = await role_repository.get_by_code(role_code)
        if role is None:
            role = Role.create(
                code=role_code,
                name=role_name,
                level=200,
                description="Роль Супер-Админа",
                is_system=True,
                is_assignable=False,
                is_wildcard=True,
                permission_codes=frozenset(),
                grantable_role_ids=frozenset(),
            )
            await role_repository.add(role)

        user_identity = await user_identity_repository.get_by_identifier_and_type(
            identifier=username, identity_type=UserIdentityType.USERNAME
        )
        if user_identity is None:
            user = User.create()
            user_identity = UserIdentity.create(
                user_id=user.id,
                identity_type=UserIdentityType.USERNAME,
                identifier=username,
            )
            password_hash = password_service.hash(password)
            user_credential = UserCredential.create(
                user_id=user.id,
                credential_type=UserCredentialType.PASSWORD,
                secret=password_hash,
            )

            await user_repository.add(user)
            await user_identity_repository.add(user_identity)
            await user_credential_repository.add(user_credential)

        role_assignment = RoleAssignment.create(
            user_id=user_identity.user_id,
            role_id=role.id,
            org_unit_id=None,
            include_descendants=True,
            granted_by_user_id=user_identity.user_id,
        )
        await role_assignment_repository.add(role_assignment)

        await transaction_manager.commit()
        print("\nСистема успешно инициализирована! Настройки применены.")


if __name__ == "__main__":
    asyncio.run(bootstrap_system())
