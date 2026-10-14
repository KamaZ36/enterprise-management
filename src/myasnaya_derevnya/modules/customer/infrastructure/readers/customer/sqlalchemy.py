from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.customer.application.dto import (
    CustomerDetail,
    CustomerListItem,
)
from myasnaya_derevnya.modules.customer.infrastructure.readers.customer.base import (
    CustomerReader,
)
from myasnaya_derevnya.modules.customer.infrastructure.tables import CUSTOMERS_TABLE


class SQLAlchemyCustomerReader(CustomerReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CustomerListItem], int]:
        conditions: list[object] = []

        if search:
            conditions.extend(
                or_(
                    CUSTOMERS_TABLE.c.first_name.ilike(
                        like_pattern(token), escape="\\"
                    ),
                    CUSTOMERS_TABLE.c.contact_phone.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        if status:
            conditions.append(CUSTOMERS_TABLE.c.status == status)

        total = await self._session.scalar(
            select(func.count()).select_from(CUSTOMERS_TABLE).where(*conditions)
        )

        rows = (
            (
                await self._session.execute(
                    select(CUSTOMERS_TABLE)
                    .where(*conditions)
                    .order_by(
                        CUSTOMERS_TABLE.c.created_at.desc(), CUSTOMERS_TABLE.c.id.desc()
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        return [self._to_item(row) for row in rows], int(total or 0)

    async def get(self, customer_id: UUID) -> CustomerDetail | None:
        row = (
            (
                await self._session.execute(
                    select(CUSTOMERS_TABLE).where(CUSTOMERS_TABLE.c.id == customer_id)
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        return CustomerDetail(
            id=row["id"],
            user_id=row["user_id"],
            first_name=row["first_name"],
            contact_phone=row["contact_phone"],
            status=row["status"],
            created_at=row["created_at"],
        )

    def _to_item(self, row: object) -> CustomerListItem:
        return CustomerListItem(
            id=row["id"],  # type: ignore[index]
            user_id=row["user_id"],  # type: ignore[index]
            first_name=row["first_name"],  # type: ignore[index]
            contact_phone=row["contact_phone"],  # type: ignore[index]
            status=row["status"],  # type: ignore[index]
            created_at=row["created_at"],  # type: ignore[index]
        )
