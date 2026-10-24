from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.fiscal.application.dto import (
    OfdBatchPostResult,
    OfdLineMappingResult,
    OfdPostResult,
    OfdReceiptDetail,
    OfdReceiptListItem,
    OfdReceiptListPage,
    OfdSyncResult,
)


class SyncOfdReceiptsSchema(BaseModel):
    reg_number: str = Field(min_length=1, max_length=32)
    date_from: datetime
    date_to: datetime


class SyncOfdReceiptsResultSchema(BaseModel):
    run_id: UUID
    status: str
    receipts_found: int
    receipts_created: int
    error: str | None

    @classmethod
    def from_dto(cls, item: OfdSyncResult) -> SyncOfdReceiptsResultSchema:
        return cls(
            run_id=item.run_id,
            status=item.status,
            receipts_found=item.receipts_found,
            receipts_created=item.receipts_created,
            error=item.error,
        )


class OfdReceiptLineSchema(BaseModel):
    id: UUID
    line_number: int
    name: str
    barcode: str | None
    quantity: Decimal
    unit: str | None
    price_kopecks: int
    total_kopecks: int
    mapping_status: str
    nomenclature_id: UUID | None
    nomenclature_name: str | None
    mapping_error: str | None


class OfdReceiptSchema(BaseModel):
    id: UUID
    reg_number: str
    doc_number: int
    fiscal_sign: str
    doc_datetime: datetime
    operation_type: str
    status: str
    total_kopecks: int
    line_count: int
    unmapped_count: int
    org_unit_id: UUID | None
    org_unit_name: str | None
    error: str | None
    posted_at: datetime | None

    @classmethod
    def from_dto(cls, item: OfdReceiptListItem) -> OfdReceiptSchema:
        return cls(
            id=item.id,
            reg_number=item.reg_number,
            doc_number=item.doc_number,
            fiscal_sign=item.fiscal_sign,
            doc_datetime=item.doc_datetime,
            operation_type=item.operation_type,
            status=item.status,
            total_kopecks=item.total_kopecks,
            line_count=item.line_count,
            unmapped_count=item.unmapped_count,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            error=item.error,
            posted_at=item.posted_at,
        )


class OfdReceiptListSchema(BaseModel):
    items: list[OfdReceiptSchema]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dto(cls, page: OfdReceiptListPage) -> OfdReceiptListSchema:
        return cls(
            items=[OfdReceiptSchema.from_dto(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class OfdReceiptDetailSchema(OfdReceiptSchema):
    inn: str
    fn_number: str
    cash_kopecks: int
    ecash_kopecks: int
    is_correction: bool
    is_bso: bool
    raw: dict
    lines: list[OfdReceiptLineSchema]

    @classmethod
    def from_dto(cls, item: OfdReceiptDetail) -> OfdReceiptDetailSchema:
        return cls(
            **OfdReceiptSchema.from_dto(item).model_dump(),
            inn=item.inn,
            fn_number=item.fn_number,
            cash_kopecks=item.cash_kopecks,
            ecash_kopecks=item.ecash_kopecks,
            is_correction=item.is_correction,
            is_bso=item.is_bso,
            raw=item.raw,
            lines=[
                OfdReceiptLineSchema(
                    id=line.id,
                    line_number=line.line_number,
                    name=line.name,
                    barcode=line.barcode,
                    quantity=line.quantity,
                    unit=line.unit,
                    price_kopecks=line.price_kopecks,
                    total_kopecks=line.total_kopecks,
                    mapping_status=line.mapping_status,
                    nomenclature_id=line.nomenclature_id,
                    nomenclature_name=line.nomenclature_name,
                    mapping_error=line.mapping_error,
                )
                for line in item.lines
            ],
        )


class MapOfdReceiptLineSchema(BaseModel):
    nomenclature_id: UUID
    remember_barcode: bool = True


class MapOfdReceiptLineResultSchema(BaseModel):
    receipt_id: UUID
    line_id: UUID
    nomenclature_id: UUID
    receipt_status: str

    @classmethod
    def from_dto(
        cls, item: OfdLineMappingResult
    ) -> MapOfdReceiptLineResultSchema:
        return cls(
            receipt_id=item.receipt_id,
            line_id=item.line_id,
            nomenclature_id=item.nomenclature_id,
            receipt_status=item.receipt_status,
        )


class OfdPostResultSchema(BaseModel):
    receipt_id: UUID
    status: str
    error: str | None

    @classmethod
    def from_dto(cls, item: OfdPostResult) -> OfdPostResultSchema:
        return cls(
            receipt_id=item.receipt_id, status=item.status, error=item.error
        )


class PostReadyOfdReceiptsSchema(BaseModel):
    limit: int = Field(default=50, ge=1, le=100)


class OfdBatchPostResultSchema(BaseModel):
    posted: int
    failed: int
    results: list[OfdPostResultSchema]

    @classmethod
    def from_dto(cls, item: OfdBatchPostResult) -> OfdBatchPostResultSchema:
        return cls(
            posted=item.posted,
            failed=item.failed,
            results=[
                OfdPostResultSchema.from_dto(result) for result in item.results
            ],
        )
