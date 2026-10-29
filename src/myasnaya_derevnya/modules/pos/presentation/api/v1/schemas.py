from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.pos.application.dto import (
    PosAgentItem,
    PosBatchPostResult,
    PosLocationItem,
    PosPostResult,
    PosProductMappingItem,
    PosReceiptDetail,
    PosReceiptLineItem,
    PosReceiptListItem,
    PosReceiptListPage,
    PosSourceItem,
    PosUnmappedProductItem,
)


class PosSourceSchema(BaseModel):
    id: UUID
    doka_org_id: str
    name: str
    org_unit_id: UUID
    org_unit_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, item: PosSourceItem) -> PosSourceSchema:
        return cls(
            id=item.id,
            doka_org_id=item.doka_org_id,
            name=item.name,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class PosLocationSchema(BaseModel):
    id: UUID
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, item: PosLocationItem) -> PosLocationSchema:
        return cls(
            id=item.id,
            name=item.name,
            is_active=item.is_active,
        )


class CreatePosSourceSchema(BaseModel):
    doka_org_id: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    org_unit_id: UUID


class UpdatePosSourceSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    org_unit_id: UUID | None = None
    is_active: bool | None = None


class PosAgentSchema(BaseModel):
    id: UUID
    source_id: UUID
    install_id: str | None
    api_key_prefix: str
    hostname: str | None
    version: str | None
    status: str
    pending_receipts: int
    last_seen_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, item: PosAgentItem) -> PosAgentSchema:
        return cls(
            id=item.id,
            source_id=item.source_id,
            install_id=item.install_id,
            api_key_prefix=item.api_key_prefix,
            hostname=item.hostname,
            version=item.version,
            status=item.status,
            pending_receipts=item.pending_receipts,
            last_seen_at=item.last_seen_at,
            last_success_at=item.last_success_at,
            last_error=item.last_error,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class IssuePosAgentKeySchema(BaseModel):
    install_id: str | None = Field(default=None, max_length=64)
    hostname: str | None = Field(default=None, max_length=255)
    version: str | None = Field(default=None, max_length=32)


class SetPosAgentActiveSchema(BaseModel):
    is_active: bool


class PosAgentKeySchema(BaseModel):
    agent: PosAgentSchema
    api_key: str


class PosReceiptLineSchema(BaseModel):
    id: UUID
    line_number: int
    product_guid: str
    product_name: str | None
    unit: str | None
    quantity: Decimal
    unit_factor: Decimal
    price_kopecks: int
    amount_kopecks: int
    discount_kopecks: int
    barcode: str | None
    mark_code: str | None
    nomenclature_id: UUID | None
    nomenclature_name: str | None
    mapping_status: str
    mapping_error: str | None

    @classmethod
    def from_dto(cls, item: PosReceiptLineItem) -> PosReceiptLineSchema:
        return cls(
            id=item.id,
            line_number=item.line_number,
            product_guid=item.product_guid,
            product_name=item.product_name,
            unit=item.unit,
            quantity=item.quantity,
            unit_factor=item.unit_factor,
            price_kopecks=item.price_kopecks,
            amount_kopecks=item.amount_kopecks,
            discount_kopecks=item.discount_kopecks,
            barcode=item.barcode,
            mark_code=item.mark_code,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            mapping_status=item.mapping_status,
            mapping_error=item.mapping_error,
        )


class PosReceiptSchema(BaseModel):
    id: UUID
    source_id: UUID
    source_name: str | None
    external_guid: str
    occurred_at: datetime
    kind: str
    payment_kind: str
    total_kopecks: int
    subdivision_name: str | None
    status: str
    error: str | None
    line_count: int
    unmapped_count: int
    posted_at: datetime | None
    org_unit_id: UUID
    org_unit_name: str | None

    @classmethod
    def from_dto(cls, item: PosReceiptListItem) -> PosReceiptSchema:
        return cls(
            id=item.id,
            source_id=item.source_id,
            source_name=item.source_name,
            external_guid=item.external_guid,
            occurred_at=item.occurred_at,
            kind=item.kind,
            payment_kind=item.payment_kind,
            total_kopecks=item.total_kopecks,
            subdivision_name=item.subdivision_name,
            status=item.status,
            error=item.error,
            line_count=item.line_count,
            unmapped_count=item.unmapped_count,
            posted_at=item.posted_at,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
        )


class PosReceiptListSchema(BaseModel):
    items: list[PosReceiptSchema]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dto(cls, page: PosReceiptListPage) -> PosReceiptListSchema:
        return cls(
            items=[PosReceiptSchema.from_dto(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class PosReceiptDetailSchema(PosReceiptSchema):
    subdivision_code: str | None
    cashier: str | None
    shift: str | None
    number: str | None
    fd_number: str | None
    fp_number: str | None
    fn_number: str | None
    raw: dict
    lines: list[PosReceiptLineSchema]

    @classmethod
    def from_dto(cls, item: PosReceiptDetail) -> PosReceiptDetailSchema:
        return cls(
            **PosReceiptSchema.from_dto(item).model_dump(),
            subdivision_code=item.subdivision_code,
            cashier=item.cashier,
            shift=item.shift,
            number=item.number,
            fd_number=item.fd_number,
            fp_number=item.fp_number,
            fn_number=item.fn_number,
            raw=item.raw,
            lines=[PosReceiptLineSchema.from_dto(line) for line in item.lines],
        )


class PostPendingPosReceiptsSchema(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)


class PosPostResultSchema(BaseModel):
    receipt_id: UUID
    status: str
    message: str | None

    @classmethod
    def from_dto(cls, item: PosPostResult) -> PosPostResultSchema:
        return cls(
            receipt_id=item.receipt_id,
            status=item.status,
            message=item.message,
        )


class PosBatchPostResultSchema(BaseModel):
    posted: int
    pending: int
    failed: int
    results: list[PosPostResultSchema]

    @classmethod
    def from_dto(cls, item: PosBatchPostResult) -> PosBatchPostResultSchema:
        return cls(
            posted=item.posted,
            pending=item.pending,
            failed=item.failed,
            results=[PosPostResultSchema.from_dto(r) for r in item.results],
        )


class PosProductMappingSchema(BaseModel):
    id: UUID
    source_id: UUID
    doka_product_guid: str
    nomenclature_id: UUID
    nomenclature_name: str | None
    unit_factor: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dto(cls, item: PosProductMappingItem) -> PosProductMappingSchema:
        return cls(
            id=item.id,
            source_id=item.source_id,
            doka_product_guid=item.doka_product_guid,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            unit_factor=item.unit_factor,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class UpsertPosProductMappingSchema(BaseModel):
    doka_product_guid: str = Field(min_length=1, max_length=64)
    nomenclature_id: UUID
    unit_factor: Decimal = Field(default=Decimal(1), gt=0)


class PosUnmappedProductSchema(BaseModel):
    product_guid: str
    product_name: str | None
    unit: str | None
    receipts_count: int
    last_seen_at: datetime

    @classmethod
    def from_dto(cls, item: PosUnmappedProductItem) -> PosUnmappedProductSchema:
        return cls(
            product_guid=item.product_guid,
            product_name=item.product_name,
            unit=item.unit,
            receipts_count=item.receipts_count,
            last_seen_at=item.last_seen_at,
        )
