from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SalesReportRow:
    day: date
    org_unit_id: UUID
    org_unit_name: str | None
    revenue_kopecks: int
    cost_kopecks: int | None
    margin_kopecks: int | None
    receipts_count: int


@dataclass(frozen=True, slots=True)
class StockReportRow:
    org_unit_id: UUID
    org_unit_name: str | None
    positions: int
    value_kopecks: int | None
    expiring_lots: int


@dataclass(frozen=True, slots=True)
class ProductionReportRow:
    org_unit_id: UUID
    org_unit_name: str | None
    tech_card_code: str
    orders_count: int
    output_quantity: Decimal
    cost_kopecks: int | None


@dataclass(frozen=True, slots=True)
class WriteOffReportRow:
    day: date
    org_unit_id: UUID
    org_unit_name: str | None
    reason: str | None
    documents_count: int
    quantity: Decimal
    cost_kopecks: int | None


@dataclass(frozen=True, slots=True)
class ReportSummary:
    revenue_kopecks: int
    cost_kopecks: int | None
    margin_kopecks: int | None
    receipts_count: int
    stock_value_kopecks: int | None
    production_orders: int
    write_off_cost_kopecks: int | None
    problem_receipts: int


@dataclass(frozen=True, slots=True)
class SalesReport:
    items: list[SalesReportRow]
    total_revenue_kopecks: int
    total_cost_kopecks: int | None
    total_margin_kopecks: int | None
    total_receipts: int
