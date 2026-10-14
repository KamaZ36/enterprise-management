from collections.abc import Collection
from uuid import UUID

from sqlalchemy import RowMapping, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.base import (
    EmployeeReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.tables import EMPLOYEES_TABLE

SEARCHED_COLUMNS = (
    EMPLOYEES_TABLE.c.last_name,
    EMPLOYEES_TABLE.c.first_name,
    EMPLOYEES_TABLE.c.middle_name,
    EMPLOYEES_TABLE.c.position,
    EMPLOYEES_TABLE.c.phone_number,
)


class SQLAlchemyEmployeeReader(EmployeeReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        org_unit_ids: Collection[UUID] | None = None,
    ) -> tuple[list[EmployeeListItem], int]:
        condition = _search_condition(search)
        scope_condition = _scope_condition(org_unit_ids)

        count_stmt = select(func.count()).select_from(EMPLOYEES_TABLE)
        stmt = (
            select(EMPLOYEES_TABLE)
            .order_by(
                EMPLOYEES_TABLE.c.last_name.asc(),
                EMPLOYEES_TABLE.c.first_name.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        for extra in (condition, scope_condition):
            if extra is not None:
                count_stmt = count_stmt.where(extra)
                stmt = stmt.where(extra)

        total = await self._session.scalar(count_stmt)
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows], total or 0

    async def get_by_id(
        self,
        employee_id: UUID,
        org_unit_ids: Collection[UUID] | None = None,
    ) -> EmployeeListItem | None:
        stmt = select(EMPLOYEES_TABLE).where(EMPLOYEES_TABLE.c.id == employee_id)

        scope_condition = _scope_condition(org_unit_ids)
        if scope_condition is not None:
            stmt = stmt.where(scope_condition)

        row = (await self._session.execute(stmt)).mappings().one_or_none()

        return self._to_dto(row) if row is not None else None

    @staticmethod
    def _to_dto(row: RowMapping) -> EmployeeListItem:
        return EmployeeListItem(
            id=row["id"],
            user_id=row["user_id"],
            org_unit_id=row["org_unit_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            middle_name=row["middle_name"],
            phone_number=row["phone_number"],
            position=row["position"],
            hired_at=row["hired_at"],
            dismissed_at=row["dismissed_at"],
            is_active=row["dismissed_at"] is None,
        )


def _scope_condition(org_unit_ids: Collection[UUID] | None):
    if org_unit_ids is None:
        return None

    return EMPLOYEES_TABLE.c.org_unit_id.in_(list(org_unit_ids))


def _search_condition(search: str | None):
    if search is None or not search.strip():
        return None

    conditions = [
        or_(
            *(
                column.ilike(like_pattern(token), escape="\\")
                for column in SEARCHED_COLUMNS
            )
        )
        for token in search.split()
    ]

    return and_(*conditions)
