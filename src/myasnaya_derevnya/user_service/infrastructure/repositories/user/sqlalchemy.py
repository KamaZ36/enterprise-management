from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.user_service.domain.entities.user import User
from myasnaya_derevnya.user_service.infrastructure.tables import (
    CUSTOMER_PROFILES_TABLE,
    EMPLOYEE_PROFILES_TABLE,
    USER_ROLES_TABLE,
    USERS_TABLE,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        stmt = insert(USERS_TABLE).values(id=user.id, created_at=user.created_at)
        await self._session.execute(stmt)

        if user.roles:
            role_bindings = [
                {"user_id": user.id, "role_slug": role.value} for role in user.roles
            ]
            await self._session.execute(USER_ROLES_TABLE.insert(), role_bindings)

        if user.customer:
            await self._session.execute(
                CUSTOMER_PROFILES_TABLE.insert().values(
                    id=user.customer.id,
                    user_id=user.id,
                    phone=user.customer.phone,
                    birth_date=user.customer.birth_date,
                )
            )

        if user.employee:
            await self._session.execute(
                EMPLOYEE_PROFILES_TABLE.insert().values(
                    id=user.employee.id,
                    user_id=user.id,
                    first_name=user.employee.first_name,
                    last_name=user.employee.last_name,
                )
            )

    async def update(self, user: User) -> None:
        await self._session.execute(
            USER_ROLES_TABLE.delete().where(USER_ROLES_TABLE.c.user_id == user.id)
        )
        if user.roles:
            role_bindings = [
                {"user_id": user.id, "role_slug": role.value} for role in user.roles
            ]
            await self._session.execute(USER_ROLES_TABLE.insert(), role_bindings)

        if user.customer:
            await self._session.execute(
                CUSTOMER_PROFILES_TABLE.update()
                .where(CUSTOMER_PROFILES_TABLE.c.user_id == user.id)
                .values(phone=user.customer.phone, birth_date=user.customer.birth_date)
            )

        if user.employee:
            await self._session.execute(
                EMPLOYEE_PROFILES_TABLE.update()
                .where(EMPLOYEE_PROFILES_TABLE.c.user_id == user.id)
                .values(
                    first_name=user.employee.first_name,
                    last_name=user.employee.last_name,
                )
            )
