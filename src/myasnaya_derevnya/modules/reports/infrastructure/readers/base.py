from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.reports.application.dto import (
    ProductionReportRow,
    ReportSummary,
    SalesReportRow,
    StockReportRow,
    WriteOffReportRow,
)


class ReportsReader(ABC):
    @abstractmethod
    async def sales(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[SalesReportRow]:
        raise NotImplementedError

    @abstractmethod
    async def stock(
        self, org_unit_ids: list[UUID] | None
    ) -> list[StockReportRow]:
        raise NotImplementedError

    @abstractmethod
    async def production(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[ProductionReportRow]:
        raise NotImplementedError

    @abstractmethod
    async def write_offs(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> list[WriteOffReportRow]:
        raise NotImplementedError

    @abstractmethod
    async def summary(
        self,
        date_from: date,
        date_to: date,
        org_unit_ids: list[UUID] | None,
    ) -> ReportSummary:
        raise NotImplementedError
