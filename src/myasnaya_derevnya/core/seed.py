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
from myasnaya_derevnya.modules.auth.services.password_service import PasswordService
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnit
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)
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

        org_unit_repository = await context.get(OrgUnitRepository)

        role_repository = await context.get(RoleRepository)
        role_assignment_repository = await context.get(RoleAssignmentRepository)

        transaction_manager = await context.get(TransactionManager)
        password_service = await context.get(PasswordService)

        root_org_unit_id = await org_unit_repository.get_root_id()
        if root_org_unit_id is None:
            root_org_unit = OrgUnit.create_root(
                code="ROOT_UNIT", name="Структурные подразделения"
            )
            await org_unit_repository.add(root_org_unit)
            root_org_unit_id = root_org_unit.id

        role = await role_repository.get_by_code(role_code)
        if role is None:
            role = Role.create(
                code=role_code,
                name=role_name,
                level=200,
                description="Супер-Админ",
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

        existing = await role_assignment_repository.load_active_for_user(
            user_id=user_identity.user_id,
        )
        already_assigned = any(
            ra.role.id == role.id and ra.assignment.org_unit_id == root_org_unit_id
            for ra in existing
        )
        if not already_assigned:
            role_assignment = RoleAssignment.create(
                user_id=user_identity.user_id,
                role_id=role.id,
                org_unit_id=root_org_unit_id,
                include_descendants=True,
                granted_by=user_identity.user_id,
            )
            await role_assignment_repository.add(role_assignment)

        await transaction_manager.commit()
        print("\nСистема успешно инициализирована! Настройки применены.")


if __name__ == "__main__":
    asyncio.run(bootstrap_system())
