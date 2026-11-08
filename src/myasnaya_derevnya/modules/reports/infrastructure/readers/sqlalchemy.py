from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_BALANCES_TABLE,
    STOCK_LOT_BALANCES_TABLE,
    STOCK_LOTS_TABLE,
    STOCK_MOVEMENTS_TABLE,
    STOCK_POSTINGS_TABLE,
    WRITE_OFF_LINES_TABLE,
    WRITE_OFFS_TABLE,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import POS_RECEIPTS_TABLE
from myasnaya_derevnya.modules.production.infrastructure.tables import (
    PRODUCTION_ORDER_LINES_TABLE,
    PRODUCTION_ORDERS_TABLE,
)
from myasnaya_derevnya.modules.reports.application.dto import (
    ProductionReportRow,
    ReportSummary,
    SalesReportRow,
    StockReportRow,
    WriteOffReportRow,
)
from myasnaya_derevnya.modules.reports.infrastructure.readers.base import (
    ReportsReader,
)

EXPIRING_DAYS = 3
PROBLEM_RECEIPT_STATUSES = ("needs_mapping", "needs_stock", "failed")


class SQLAlchemyReportsReader(ReportsReader):
    """Read-model для отчётов.

    Аналитика читает таблицы нескольких модулей напрямую: это осознанное
    исключение из правила «только через фасад», чтобы не тащить отчётные
    запросы в доменные сервисы.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sales(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[SalesReportRow]:
        if org_unit_ids is not None and not org_unit_ids:
            return []

        start, end = _period(date_from, date_to)
        cost = _sale_cost_subquery().subquery()
        day = func.date_trunc("day", POS_RECEIPTS_TABLE.c.occurred_at).label("day")

        stmt = (
            select(
                day,
                POS_RECEIPTS_TABLE.c.org_unit_id,
                func.sum(POS_RECEIPTS_TABLE.c.total_kopecks).label("revenue"),
                func.count(POS_RECEIPTS_TABLE.c.id).label("receipts"),
                func.coalesce(func.sum(cost.c.cost_kopecks), 0).label("cost"),
            )
            .select_from(
                POS_RECEIPTS_TABLE.outerjoin(
                    cost, cost.c.document_id == POS_RECEIPTS_TABLE.c.id
                )
            )
            .where(
                POS_RECEIPTS_TABLE.c.status == "posted",
                POS_RECEIPTS_TABLE.c.kind == "sale",
                POS_RECEIPTS_TABLE.c.occurred_at >= start,
                POS_RECEIPTS_TABLE.c.occurred_at < end,
            )
            .group_by(day, POS_RECEIPTS_TABLE.c.org_unit_id)
            .order_by(day, POS_RECEIPTS_TABLE.c.org_unit_id)
        )
        rows = (await self._session.execute(self._filter(stmt, POS_RECEIPTS_TABLE.c.org_unit_id, org_unit_ids))).mappings().all()

        return [
            SalesReportRow(
                day=_as_date(row["day"]),
                org_unit_id=row["org_unit_id"],
                org_unit_name=None,
                revenue_kopecks=int(row["revenue"] or 0),
                cost_kopecks=int(row["cost"] or 0),
                margin_kopecks=int(row["revenue"] or 0) - int(row["cost"] or 0),
                receipts_count=int(row["receipts"] or 0),
            )
            for row in rows
        ]

    async def stock(
        self, org_unit_ids: list[UUID] | None
    ) -> list[StockReportRow]:
        if org_unit_ids is not None and not org_unit_ids:
            return []

        today = datetime.now(UTC).date()
        expiring = (
            select(
                STOCK_LOT_BALANCES_TABLE.c.org_unit_id,
                func.count(distinct(STOCK_LOT_BALANCES_TABLE.c.lot_id)).label(
                    "expiring_lots"
                ),
            )
            .select_from(
                STOCK_LOT_BALANCES_TABLE.join(
                    STOCK_LOTS_TABLE,
                    STOCK_LOTS_TABLE.c.id == STOCK_LOT_BALANCES_TABLE.c.lot_id,
                )
            )
            .where(
                STOCK_LOT_BALANCES_TABLE.c.quantity > 0,
                STOCK_LOTS_TABLE.c.expires_at.is_not(None),
                STOCK_LOTS_TABLE.c.expires_at >= today,
                STOCK_LOTS_TABLE.c.expires_at <= today + timedelta(days=EXPIRING_DAYS),
            )
            .group_by(STOCK_LOT_BALANCES_TABLE.c.org_unit_id)
            .subquery()
        )

        stmt = (
            select(
                STOCK_BALANCES_TABLE.c.org_unit_id,
                func.count().label("positions"),
                func.coalesce(func.sum(STOCK_BALANCES_TABLE.c.total_value), 0).label(
                    "value_kopecks"
                ),
                func.coalesce(expiring.c.expiring_lots, 0).label("expiring_lots"),
            )
            .select_from(
                STOCK_BALANCES_TABLE.outerjoin(
                    expiring, expiring.c.org_unit_id == STOCK_BALANCES_TABLE.c.org_unit_id
                )
            )
            .where(STOCK_BALANCES_TABLE.c.quantity > 0)
            .group_by(STOCK_BALANCES_TABLE.c.org_unit_id, expiring.c.expiring_lots)
            .order_by(STOCK_BALANCES_TABLE.c.org_unit_id)
        )
        rows = (await self._session.execute(self._filter(stmt, STOCK_BALANCES_TABLE.c.org_unit_id, org_unit_ids))).mappings().all()

        return [
            StockReportRow(
                org_unit_id=row["org_unit_id"],
                org_unit_name=None,
                positions=int(row["positions"] or 0),
                value_kopecks=int(row["value_kopecks"] or 0),
                expiring_lots=int(row["expiring_lots"] or 0),
            )
            for row in rows
        ]

    async def production(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[ProductionReportRow]:
        if org_unit_ids is not None and not org_unit_ids:
            return []

        start, end = _period(date_from, date_to)
        stmt = (
            select(
                PRODUCTION_ORDERS_TABLE.c.org_unit_id,
                PRODUCTION_ORDERS_TABLE.c.tech_card_code,
                func.count(distinct(PRODUCTION_ORDERS_TABLE.c.id)).label("orders"),
                func.coalesce(
                    func.sum(PRODUCTION_ORDER_LINES_TABLE.c.actual_quantity), 0
                ).label("output_quantity"),
                func.coalesce(
                    func.sum(PRODUCTION_ORDER_LINES_TABLE.c.cost), 0
                ).label("cost_kopecks"),
            )
            .select_from(
                PRODUCTION_ORDERS_TABLE.join(
                    PRODUCTION_ORDER_LINES_TABLE,
                    PRODUCTION_ORDER_LINES_TABLE.c.order_id
                    == PRODUCTION_ORDERS_TABLE.c.id,
                )
            )
            .where(
                PRODUCTION_ORDERS_TABLE.c.status == "posted",
                PRODUCTION_ORDER_LINES_TABLE.c.role == "output",
                PRODUCTION_ORDERS_TABLE.c.occurred_at >= start,
                PRODUCTION_ORDERS_TABLE.c.occurred_at < end,
            )
            .group_by(
                PRODUCTION_ORDERS_TABLE.c.org_unit_id,
                PRODUCTION_ORDERS_TABLE.c.tech_card_code,
            )
            .order_by(
                PRODUCTION_ORDERS_TABLE.c.org_unit_id,
                PRODUCTION_ORDERS_TABLE.c.tech_card_code,
            )
        )
        rows = (await self._session.execute(self._filter(stmt, PRODUCTION_ORDERS_TABLE.c.org_unit_id, org_unit_ids))).mappings().all()

        return [
            ProductionReportRow(
                org_unit_id=row["org_unit_id"],
                org_unit_name=None,
                tech_card_code=row["tech_card_code"],
                orders_count=int(row["orders"] or 0),
                output_quantity=row["output_quantity"],
                cost_kopecks=int(row["cost_kopecks"] or 0),
            )
            for row in rows
        ]

    async def write_offs(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[WriteOffReportRow]:
        if org_unit_ids is not None and not org_unit_ids:
            return []

        start, end = _period(date_from, date_to)
        quantity = (
            select(
                WRITE_OFF_LINES_TABLE.c.write_off_id,
                func.sum(WRITE_OFF_LINES_TABLE.c.quantity).label("quantity"),
            )
            .group_by(WRITE_OFF_LINES_TABLE.c.write_off_id)
            .subquery()
        )
        cost = _write_off_cost_subquery().subquery()
        day = func.date_trunc("day", WRITE_OFFS_TABLE.c.occurred_at).label("day")

        stmt = (
            select(
                day,
                WRITE_OFFS_TABLE.c.org_unit_id,
                WRITE_OFFS_TABLE.c.reason,
                func.count(distinct(WRITE_OFFS_TABLE.c.id)).label("documents"),
                func.coalesce(func.sum(quantity.c.quantity), 0).label("quantity"),
                func.coalesce(func.sum(cost.c.cost_kopecks), 0).label("cost"),
            )
            .select_from(
                WRITE_OFFS_TABLE.outerjoin(
                    quantity, quantity.c.write_off_id == WRITE_OFFS_TABLE.c.id
                ).outerjoin(cost, cost.c.document_id == WRITE_OFFS_TABLE.c.id)
            )
            .where(
                WRITE_OFFS_TABLE.c.status == "posted",
                WRITE_OFFS_TABLE.c.occurred_at >= start,
                WRITE_OFFS_TABLE.c.occurred_at < end,
            )
            .group_by(day, WRITE_OFFS_TABLE.c.org_unit_id, WRITE_OFFS_TABLE.c.reason)
            .order_by(day, WRITE_OFFS_TABLE.c.org_unit_id)
        )
        rows = (await self._session.execute(self._filter(stmt, WRITE_OFFS_TABLE.c.org_unit_id, org_unit_ids))).mappings().all()

        return [
            WriteOffReportRow(
                day=_as_date(row["day"]),
                org_unit_id=row["org_unit_id"],
                org_unit_name=None,
                reason=row["reason"],
                documents_count=int(row["documents"] or 0),
                quantity=row["quantity"] or 0,
                cost_kopecks=int(row["cost"] or 0),
            )
            for row in rows
        ]

    async def summary(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> ReportSummary:
        sales = await self.sales(date_from, date_to, org_unit_ids)
        stock = await self.stock(org_unit_ids)
        production = await self.production(date_from, date_to, org_unit_ids)
        write_offs = await self.write_offs(date_from, date_to, org_unit_ids)

        revenue = sum(row.revenue_kopecks for row in sales)
        cost = sum(row.cost_kopecks for row in sales)
        receipts = sum(row.receipts_count for row in sales)

        return ReportSummary(
            revenue_kopecks=revenue,
            cost_kopecks=cost,
            margin_kopecks=revenue - cost,
            receipts_count=receipts,
            stock_value_kopecks=sum(row.value_kopecks for row in stock),
            production_orders=sum(row.orders_count for row in production),
            write_off_cost_kopecks=sum(row.cost_kopecks for row in write_offs),
            problem_receipts=await self._problem_receipts(org_unit_ids),
        )

    async def _problem_receipts(self, org_unit_ids: list[UUID] | None) -> int:
        if org_unit_ids is not None and not org_unit_ids:
            return 0

        stmt = (
            select(func.count())
            .select_from(POS_RECEIPTS_TABLE)
            .where(POS_RECEIPTS_TABLE.c.status.in_(PROBLEM_RECEIPT_STATUSES))
        )
        stmt = self._filter(stmt, POS_RECEIPTS_TABLE.c.org_unit_id, org_unit_ids)
        return int(await self._session.scalar(stmt) or 0)

    @staticmethod
    def _filter(
        stmt: Select,
        column,
        org_unit_ids: list[UUID] | None,
    ) -> Select:
        if org_unit_ids is None:
            return stmt

        return stmt.where(column.in_(org_unit_ids))


def _period(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min, tzinfo=UTC)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)

    return start, end


def _sale_cost_subquery():
    return (
        select(
            STOCK_POSTINGS_TABLE.c.document_id,
            func.sum(-STOCK_MOVEMENTS_TABLE.c.total_cost).label("cost_kopecks"),
        )
        .select_from(
            STOCK_MOVEMENTS_TABLE.join(
                STOCK_POSTINGS_TABLE,
                STOCK_POSTINGS_TABLE.c.id == STOCK_MOVEMENTS_TABLE.c.posting_id,
            )
        )
        .where(STOCK_MOVEMENTS_TABLE.c.movement_type == "sale")
        .group_by(STOCK_POSTINGS_TABLE.c.document_id)
    )


def _write_off_cost_subquery():
    return (
        select(
            STOCK_POSTINGS_TABLE.c.document_id,
            func.sum(-STOCK_MOVEMENTS_TABLE.c.total_cost).label("cost_kopecks"),
        )
        .select_from(
            STOCK_MOVEMENTS_TABLE.join(
                STOCK_POSTINGS_TABLE,
                STOCK_POSTINGS_TABLE.c.id == STOCK_MOVEMENTS_TABLE.c.posting_id,
            )
        )
        .where(STOCK_MOVEMENTS_TABLE.c.movement_type == "write_off")
        .group_by(STOCK_POSTINGS_TABLE.c.document_id)
    )


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()

    return value
