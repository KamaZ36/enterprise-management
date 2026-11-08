from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.reports.application.dto import (
    ProductionReportRow,
    ReportSummary,
    SalesReport,
    SalesReportRow,
    StockReportRow,
    TurnoverReportRow,
    WriteOffReportRow,
)


class ReportSummarySchema(BaseModel):
    revenue_kopecks: int
    cost_kopecks: int | None
    margin_kopecks: int | None
    receipts_count: int
    stock_value_kopecks: int | None
    production_orders: int
    write_off_cost_kopecks: int | None
    problem_receipts: int

    @classmethod
    def from_dto(cls, item: ReportSummary) -> ReportSummarySchema:
        return cls(
            revenue_kopecks=item.revenue_kopecks,
            cost_kopecks=item.cost_kopecks,
            margin_kopecks=item.margin_kopecks,
            receipts_count=item.receipts_count,
            stock_value_kopecks=item.stock_value_kopecks,
            production_orders=item.production_orders,
            write_off_cost_kopecks=item.write_off_cost_kopecks,
            problem_receipts=item.problem_receipts,
        )


class SalesReportRowSchema(BaseModel):
    day: date
    org_unit_id: UUID
    org_unit_name: str | None
    revenue_kopecks: int
    cost_kopecks: int
    margin_kopecks: int
    receipts_count: int

    @classmethod
    def from_dto(cls, item: SalesReportRow) -> SalesReportRowSchema:
        return cls(
            day=item.day,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            revenue_kopecks=item.revenue_kopecks,
            cost_kopecks=item.cost_kopecks,
            margin_kopecks=item.margin_kopecks,
            receipts_count=item.receipts_count,
        )


class SalesReportSchema(BaseModel):
    items: list[SalesReportRowSchema]
    total_revenue_kopecks: int
    total_cost_kopecks: int | None
    total_margin_kopecks: int | None
    total_receipts: int

    @classmethod
    def from_dto(cls, report: SalesReport) -> SalesReportSchema:
        return cls(
            items=[SalesReportRowSchema.from_dto(item) for item in report.items],
            total_revenue_kopecks=report.total_revenue_kopecks,
            total_cost_kopecks=report.total_cost_kopecks,
            total_margin_kopecks=report.total_margin_kopecks,
            total_receipts=report.total_receipts,
        )


class StockReportRowSchema(BaseModel):
    org_unit_id: UUID
    org_unit_name: str | None
    positions: int
    value_kopecks: int | None
    expiring_lots: int

    @classmethod
    def from_dto(cls, item: StockReportRow) -> StockReportRowSchema:
        return cls(
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            positions=item.positions,
            value_kopecks=item.value_kopecks,
            expiring_lots=item.expiring_lots,
        )


class StockReportSchema(BaseModel):
    items: list[StockReportRowSchema]


class TurnoverReportRowSchema(BaseModel):
    org_unit_id: UUID
    org_unit_name: str | None
    nomenclature_id: UUID
    nomenclature_name: str
    sku: str
    unit: str
    opening_quantity: Decimal
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    closing_quantity: Decimal
    opening_value_kopecks: int | None = None
    inbound_value_kopecks: int | None = None
    outbound_value_kopecks: int | None = None
    closing_value_kopecks: int | None = None

    @classmethod
    def from_dto(
        cls, item: TurnoverReportRow
    ) -> TurnoverReportRowSchema:
        return cls(
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            sku=item.sku,
            unit=item.unit,
            opening_quantity=item.opening_quantity,
            inbound_quantity=item.inbound_quantity,
            outbound_quantity=item.outbound_quantity,
            closing_quantity=item.closing_quantity,
            opening_value_kopecks=item.opening_value_kopecks,
            inbound_value_kopecks=item.inbound_value_kopecks,
            outbound_value_kopecks=item.outbound_value_kopecks,
            closing_value_kopecks=item.closing_value_kopecks,
        )


class TurnoverReportSchema(BaseModel):
    items: list[TurnoverReportRowSchema]


class ProductionReportRowSchema(BaseModel):
    org_unit_id: UUID
    org_unit_name: str | None
    tech_card_code: str
    orders_count: int
    output_quantity: Decimal
    cost_kopecks: int | None

    @classmethod
    def from_dto(cls, item: ProductionReportRow) -> ProductionReportRowSchema:
        return cls(
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            tech_card_code=item.tech_card_code,
            orders_count=item.orders_count,
            output_quantity=item.output_quantity,
            cost_kopecks=item.cost_kopecks,
        )


class ProductionReportSchema(BaseModel):
    items: list[ProductionReportRowSchema]


class WriteOffReportRowSchema(BaseModel):
    day: date
    org_unit_id: UUID
    org_unit_name: str | None
    reason: str | None
    documents_count: int
    quantity: Decimal
    cost_kopecks: int | None

    @classmethod
    def from_dto(cls, item: WriteOffReportRow) -> WriteOffReportRowSchema:
        return cls(
            day=item.day,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            reason=item.reason,
            documents_count=item.documents_count,
            quantity=item.quantity,
            cost_kopecks=item.cost_kopecks,
        )


class WriteOffReportSchema(BaseModel):
    items: list[WriteOffReportRowSchema]
