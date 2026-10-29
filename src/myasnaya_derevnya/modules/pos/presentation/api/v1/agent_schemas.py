from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.pos.application.dto import (
    IncomingReceipt,
    IncomingReceiptLine,
    PosHeartbeatResult,
    PosImportResult,
)


class AgentSourceSchema(BaseModel):
    doka_org_id: str = Field(min_length=1, max_length=32)


class AgentInfoSchema(BaseModel):
    install_id: str = Field(min_length=1, max_length=64)
    version: str | None = Field(default=None, max_length=32)
    hostname: str | None = Field(default=None, max_length=255)
    clock_utc: datetime | None = None


class AgentFileSchema(BaseModel):
    name: str = Field(min_length=1, max_length=512)
    sha256: str | None = Field(default=None, max_length=64)
    exported_at: datetime | None = None


class AgentReceiptLineSchema(BaseModel):
    guid: str | None = Field(default=None, max_length=64)
    product_guid: str = Field(min_length=1, max_length=64)
    product_name: str | None = Field(default=None, max_length=512)
    unit: str | None = Field(default=None, max_length=32)
    quantity: Decimal = Field(gt=0)
    price_kopecks: int = Field(ge=0)
    amount_kopecks: int = Field(ge=0)
    discount_kopecks: int = Field(default=0, ge=0)
    barcode: str | None = Field(default=None, max_length=64)
    mark_code: str | None = Field(default=None, max_length=128)

    def to_dto(self) -> IncomingReceiptLine:
        return IncomingReceiptLine(
            guid=self.guid,
            product_guid=self.product_guid,
            product_name=self.product_name,
            unit=self.unit,
            quantity=self.quantity,
            price_kopecks=self.price_kopecks,
            amount_kopecks=self.amount_kopecks,
            discount_kopecks=self.discount_kopecks,
            barcode=self.barcode,
            mark_code=self.mark_code,
            raw=self.model_dump(mode="json"),
        )


class AgentReceiptSchema(BaseModel):
    guid: str = Field(min_length=32, max_length=64)
    occurred_at: datetime
    kind: Literal["sale", "return"] = "sale"
    payment_kind: str = Field(min_length=1, max_length=32)
    total_kopecks: int = Field(ge=0)
    subdivision_code: str | None = Field(default=None, max_length=32)
    subdivision_name: str | None = Field(default=None, max_length=255)
    cashier: str | None = Field(default=None, max_length=255)
    shift: str | None = Field(default=None, max_length=32)
    number: str | None = Field(default=None, max_length=32)
    fd_number: str | None = Field(default=None, max_length=32)
    fp_number: str | None = Field(default=None, max_length=32)
    fn_number: str | None = Field(default=None, max_length=32)
    warnings: list[str] = Field(default_factory=list)
    lines: list[AgentReceiptLineSchema] = Field(default_factory=list)

    def to_dto(self) -> IncomingReceipt:
        return IncomingReceipt(
            guid=self.guid,
            occurred_at=self.occurred_at,
            kind=self.kind,
            payment_kind=self.payment_kind,
            total_kopecks=self.total_kopecks,
            subdivision_code=self.subdivision_code,
            subdivision_name=self.subdivision_name,
            cashier=self.cashier,
            shift=self.shift,
            number=self.number,
            fd_number=self.fd_number,
            fp_number=self.fp_number,
            fn_number=self.fn_number,
            warnings=tuple(self.warnings),
            lines=tuple(line.to_dto() for line in self.lines),
            raw=self.model_dump(mode="json"),
        )


class ImportPosReceiptsSchema(BaseModel):
    source: AgentSourceSchema
    agent: AgentInfoSchema
    file: AgentFileSchema
    receipts: list[AgentReceiptSchema] = Field(min_length=1)


class ImportPosReceiptResultSchema(BaseModel):
    guid: str
    status: str
    message: str | None = None


class ImportPosReceiptsResultSchema(BaseModel):
    server_time: datetime
    batch_id: UUID
    results: list[ImportPosReceiptResultSchema]

    @classmethod
    def from_dto(cls, result: PosImportResult) -> ImportPosReceiptsResultSchema:
        return cls(
            server_time=result.server_time,
            batch_id=result.batch_id,
            results=[
                ImportPosReceiptResultSchema(
                    guid=item.guid,
                    status=item.status,
                    message=item.message,
                )
                for item in result.results
            ],
        )


class HeartbeatSchema(BaseModel):
    install_id: str = Field(min_length=1, max_length=64)
    version: str | None = Field(default=None, max_length=32)
    hostname: str | None = Field(default=None, max_length=255)
    source: AgentSourceSchema
    status: str = Field(default="ok", max_length=16)
    pending_receipts: int = Field(default=0, ge=0)
    last_success_at: datetime | None = None
    last_error: str | None = Field(default=None, max_length=1024)
    clock_utc: datetime | None = None


class HeartbeatResultSchema(BaseModel):
    server_time: datetime

    @classmethod
    def from_dto(cls, result: PosHeartbeatResult) -> HeartbeatResultSchema:
        return cls(server_time=result.server_time)
