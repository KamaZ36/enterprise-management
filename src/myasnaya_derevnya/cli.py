import argparse
import asyncio
import getpass
import os
from uuid import UUID, uuid7

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.sqlalchemy import (
    SQLAlchemyCredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.sqlalchemy import (
    SQLAlchemyUserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.sqlalchemy import (
    SQLAlchemyUserRepository,
)
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.sqlalchemy import (
    SQLAlchemyRoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.sqlalchemy import (
    SQLAlchemyRoleAssignmentRepository,
)


async def seed_roles() -> None:
    engine = create_async_engine(settings.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        role_repo = SQLAlchemyRoleRepository(session)

        existing = await role_repo.get_by_code("system_admin")
        if existing is not None:
            print("system_admin already exists")
            return

        role = Role.create(
            code="system_admin",
            name="Системный администратор",
            level=100,
            description="Полный доступ",
            is_system=True,
            is_assignable=False,
            is_wildcard=True,
        )
        await role_repo.add(role)
        await session.commit()

        print(f"Role created: {role.code}, id={role.id}")

    await engine.dispose()


async def seed_admin(login: str, password: str, root_id: UUID) -> None:
    engine = create_async_engine(settings.db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        user_repo = SQLAlchemyUserRepository(session)
        cred_repo = SQLAlchemyCredentialRepository(session)
        identity_repo = SQLAlchemyUserIdentityRepository(session)
        role_repo = SQLAlchemyRoleRepository(session)
        assignment_repo = SQLAlchemyRoleAssignmentRepository(session)
        hasher = PasswordService()

        # 1. Проверка идемпотентности
        existing = await identity_repo.get_by_identifier_and_type(
            identifier="admin", identity_type=UserIdentityType.USERNAME
        )
        if existing is not None:
            print(f"Admin {login} already exists")
            return
        # 2. Роль system_admin
        admin_role = await role_repo.get_by_code("system_admin")
        if admin_role is None:
            print("system_admin role not found. Run seed-roles first.")
            return
        # 3. User
        user = User.create()
        await user_repo.add(user)
        # 4. Password
        credential = UserCredential.create(
            user_id=user.id,
            credential_type=UserCredentialType.PASSWORD,
            secret=hasher.hash(password),
        )
        await cred_repo.add(credential)
        # 5. Identity
        identity = UserIdentity.create(
            user_id=user.id,
            identity_type=UserIdentityType.USERNAME,
            identifier=login,
        )
        await identity_repo.add(identity)
        # 6. RoleAssignment
        assignment = RoleAssignment.create(
            user_id=user.id,
            role_id=admin_role.id,
            org_unit_id=root_id,
            granted_by_user_id=user.id,
            include_descendants=True,
        )
        await assignment_repo.add(assignment)

        print(f"Admin created: {login}")
        print(f"User ID: {user.id}")

        await session.commit()

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed-roles", help="Create base roles")
    admin_parser = sub.add_parser("seed-admin", help="Create system admin")
    admin_parser.add_argument("--login", default=os.environ.get("ADMIN_LOGIN"))
    admin_parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    admin_parser.add_argument(
        "--root-id",
        default=os.environ.get("ROOT_ORG_UNIT_ID"),
        help="Root org unit UUID",
    )

    args = parser.parse_args()

    if args.command == "seed-roles":
        asyncio.run(seed_roles())

    if args.command == "seed-admin":
        login = args.login or input("Login: ")
        password = args.password or getpass.getpass("Password: ")
        root_id = UUID(args.root_id) if args.root_id else _prompt_root_id()

        asyncio.run(seed_admin(login, password, root_id))


def _prompt_root_id() -> UUID:
    return uuid7()


if __name__ == "__main__":
    main()
