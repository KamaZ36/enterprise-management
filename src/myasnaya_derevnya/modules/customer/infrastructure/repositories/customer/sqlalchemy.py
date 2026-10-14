from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.customer.domain.entities.customer import (
    Customer,
    CustomerStatus,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.base import (
    CustomerRepository,
)
from myasnaya_derevnya.modules.customer.infrastructure.tables import CUSTOMERS_TABLE


class SQLAlchemyCustomerRepository(CustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, customer: Customer) -> None:
        stmt = insert(CUSTOMERS_TABLE).values(
            id=customer.id,
            user_id=customer.user_id,
            first_name=customer.first_name,
            contact_phone=customer.contact_phone,
            status=customer.status.value,
            created_at=customer.created_at,
        )
        await self._session.execute(stmt)

    async def get_by_user_id(self, user_id: UUID) -> Customer | None:
        query = select(CUSTOMERS_TABLE).where(CUSTOMERS_TABLE.c.user_id == user_id)
        result = await self._session.execute(query)
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        query = select(CUSTOMERS_TABLE).where(CUSTOMERS_TABLE.c.id == customer_id)
        row = (await self._session.execute(query)).mappings().one_or_none()

        return self._to_entity(row) if row is not None else None

    def _to_entity(self, row: RowMapping) -> Customer:
        return Customer(
            id=row["id"],
            user_id=row["user_id"],
            first_name=row["first_name"],
            contact_phone=row["contact_phone"],
            status=CustomerStatus(row["status"]),
            created_at=row["created_at"],
        )
