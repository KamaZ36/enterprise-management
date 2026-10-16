
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.dto import (
    LocationListItem,
    ReceiptDetail,
    ReceiptLineItem,
    ReceiptListItem,
    TransferDetail,
    TransferLineItem,
    TransferListItem,
    WriteOffDetail,
    WriteOffLineItem,
    WriteOffListItem,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.get import (
    GetReceiptInteractor,
    GetReceiptQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.list import (
    ListReceiptsInteractor,
    ListReceiptsQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.get import (
    GetTransferInteractor,
    GetTransferQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.list import (
    ListTransfersInteractor,
    ListTransfersQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.get import (
    GetWriteOffInteractor,
    GetWriteOffQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.list import (
    ListWriteOffsInteractor,
    ListWriteOffsQuery,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    ReceiptNotFoundError,
    TransferNotFoundError,
    WriteOffNotFoundError,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)

OCCURRED_AT = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
READ_DOCUMENTS = "inventory.document.read"


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(
        self,
        allowed: bool = True,
        scope: AccessScope | None = None,
        allowed_units: set[UUID] | None = None,
    ) -> None:
        self.allowed = allowed
        self.scope = scope if scope is not None else AccessScope.company_wide()
        self.allowed_units = allowed_units
        self.can_calls: list[tuple[str, UUID | None]] = []
        self.scope_calls: list[str] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.can_calls.append((permission.code, org_unit_id))
        if self.allowed_units is not None:
            return org_unit_id in self.allowed_units
        return self.allowed

    async def scope_for(self, user_id: UUID, permission) -> AccessScope:
        self.scope_calls.append(permission.code)
        return self.scope


class FakeBusinessAPI:
    def __init__(self, locations: list[LocationListItem] | None = None) -> None:
        self.locations = locations or []
        self.stock_locations_calls = 0

    async def stock_locations(self) -> list[LocationListItem]:
        self.stock_locations_calls += 1
        return self.locations


class FakeCatalogAPI:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}
        self.calls: list[set[UUID]] = []

    async def nomenclature_names(self, nomenclature_ids) -> dict[UUID, str]:
        self.calls.append(set(nomenclature_ids))
        return {key: self.names[key] for key in nomenclature_ids if key in self.names}


class FakeReceiptReader:
    def __init__(self, detail: ReceiptDetail | None = None) -> None:
        self.items: list[ReceiptListItem] = []
        self.detail = detail
        self.list_calls: list[dict] = []
        self.get_calls: list[UUID] = []

    async def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.items, len(self.items)

    async def get(self, receipt_id: UUID) -> ReceiptDetail | None:
        self.get_calls.append(receipt_id)
        return self.detail


class FakeTransferReader:
    def __init__(self, detail: TransferDetail | None = None) -> None:
        self.items: list[TransferListItem] = []
        self.detail = detail
        self.list_calls: list[dict] = []
        self.get_calls: list[UUID] = []

    async def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.items, len(self.items)

    async def get(self, transfer_id: UUID) -> TransferDetail | None:
        self.get_calls.append(transfer_id)
        return self.detail


class FakeWriteOffReader:
    def __init__(self, detail: WriteOffDetail | None = None) -> None:
        self.items: list[WriteOffListItem] = []
        self.detail = detail
        self.list_calls: list[dict] = []
        self.get_calls: list[UUID] = []

    async def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.items, len(self.items)

    async def get(self, write_off_id: UUID) -> WriteOffDetail | None:
        self.get_calls.append(write_off_id)
        return self.detail


def make_location_item(org_unit_id: UUID, name: str = "Локация") -> LocationListItem:
    return LocationListItem(id=org_unit_id, name=name, is_active=True)


def make_document_scope(
    *,
    scope: AccessScope | None = None,
    locations: list[LocationListItem] | None = None,
    allowed: bool = True,
    allowed_units: set[UUID] | None = None,
) -> tuple[DocumentScope, FakeBusinessAPI, FakeStaffAPI]:
    business_api = FakeBusinessAPI(locations)
    staff_api = FakeStaffAPI(
        allowed=allowed,
        scope=scope,
        allowed_units=allowed_units,
    )
    document_scope = DocumentScope(
        identity_provider=FakeIdentityProvider(),
        business_api=business_api,
        staff_api=staff_api,
    )

    return document_scope, business_api, staff_api


def make_receipt_detail(
    nomenclature_id: UUID, org_unit_id: UUID | None = None
) -> ReceiptDetail:
    return ReceiptDetail(
        id=uuid4(),
        org_unit_id=org_unit_id or uuid4(),
        status="posted",
        occurred_at=OCCURRED_AT,
        posted_at=OCCURRED_AT,
        supplier_name="Мясокомбинат",
        supplier_document_number="УПД-1",
        comment=None,
        lines=[
            ReceiptLineItem(
                id=uuid4(),
                nomenclature_id=nomenclature_id,
                quantity=Decimal("40.5"),
                unit_cost=Decimal("450.5"),
                total_kopecks=1824525,
                lot_code="L-001",
                expires_at=date(2026, 11, 5),
            )
        ],
    )


def make_transfer_detail(
    nomenclature_id: UUID,
    *,
    from_org_unit_id: UUID | None = None,
    to_org_unit_id: UUID | None = None,
) -> TransferDetail:
    return TransferDetail(
        id=uuid4(),
        from_org_unit_id=from_org_unit_id or uuid4(),
        to_org_unit_id=to_org_unit_id or uuid4(),
        status="posted",
        occurred_at=OCCURRED_AT,
        posted_at=OCCURRED_AT,
        comment="Перевозка",
        lines=[
            TransferLineItem(
                id=uuid4(),
                nomenclature_id=nomenclature_id,
                quantity=Decimal(2),
                lot_code="L-001",
            )
        ],
    )


def make_write_off_detail(
    nomenclature_id: UUID, org_unit_id: UUID | None = None
) -> WriteOffDetail:
    return WriteOffDetail(
        id=uuid4(),
        org_unit_id=org_unit_id or uuid4(),
        status="posted",
        occurred_at=OCCURRED_AT,
        posted_at=OCCURRED_AT,
        reason="Просрочка",
        comment=None,
        lines=[
            WriteOffLineItem(
                id=uuid4(),
                nomenclature_id=nomenclature_id,
                quantity=Decimal("1.5"),
                lot_code="L-001",
            )
        ],
    )


def build_list_receipts(
    *,
    scope: AccessScope | None = None,
    locations: list[LocationListItem] | None = None,
) -> tuple[ListReceiptsInteractor, FakeReceiptReader]:
    reader = FakeReceiptReader()
    document_scope, _, _ = make_document_scope(scope=scope, locations=locations)
    interactor = ListReceiptsInteractor(
        receipt_reader=reader,
        document_scope=document_scope,
    )

    return interactor, reader


def build_list_transfers(
    *,
    scope: AccessScope | None = None,
    locations: list[LocationListItem] | None = None,
) -> tuple[ListTransfersInteractor, FakeTransferReader]:
    reader = FakeTransferReader()
    document_scope, _, _ = make_document_scope(scope=scope, locations=locations)
    interactor = ListTransfersInteractor(
        transfer_reader=reader,
        document_scope=document_scope,
    )

    return interactor, reader


def build_list_write_offs() -> tuple[ListWriteOffsInteractor, FakeWriteOffReader]:
    reader = FakeWriteOffReader()
    document_scope, _, _ = make_document_scope()

    return (
        ListWriteOffsInteractor(
            write_off_reader=reader,
            document_scope=document_scope,
        ),
        reader,
    )


def build_get_receipt(
    detail: ReceiptDetail | None,
    *,
    allowed: bool = True,
    allowed_units: set[UUID] | None = None,
    catalog_api: FakeCatalogAPI | None = None,
) -> tuple[GetReceiptInteractor, FakeReceiptReader, FakeStaffAPI]:
    reader = FakeReceiptReader(detail=detail)
    document_scope, _, staff_api = make_document_scope(
        allowed=allowed, allowed_units=allowed_units
    )
    interactor = GetReceiptInteractor(
        receipt_reader=reader,
        catalog_api=catalog_api or FakeCatalogAPI(),
        document_scope=document_scope,
    )

    return interactor, reader, staff_api


async def test_journal_requires_read_permission() -> None:
    interactor, reader = build_list_receipts(scope=AccessScope.of([]))

    with pytest.raises(ForbiddenError):
        await interactor(ListReceiptsQuery())

    assert reader.list_calls == []


async def test_receipt_journal_passes_location_filter_and_window() -> None:
    interactor, reader = build_list_receipts()
    org_unit_id = uuid4()

    page = await interactor(
        ListReceiptsQuery(org_unit_id=org_unit_id, limit=10, offset=20)
    )

    assert reader.list_calls == [
        {"org_unit_ids": [org_unit_id], "limit": 10, "offset": 20, "search": None}
    ]
    assert (page.limit, page.offset, page.total) == (10, 20, 0)


async def test_receipt_journal_is_limited_to_scope_locations() -> None:
    own_unit, other_unit = uuid4(), uuid4()
    own = make_location_item(own_unit)
    other = make_location_item(other_unit)
    interactor, reader = build_list_receipts(
        scope=AccessScope.of([own_unit]), locations=[own, other]
    )

    await interactor(ListReceiptsQuery())

    assert reader.list_calls == [
        {"org_unit_ids": [own.id], "limit": 20, "offset": 0, "search": None}
    ]


async def test_receipt_journal_denies_foreign_location() -> None:
    own_unit = uuid4()
    own = make_location_item(own_unit)
    foreign = make_location_item(uuid4())
    interactor, reader = build_list_receipts(
        scope=AccessScope.of([own_unit]), locations=[own, foreign]
    )

    with pytest.raises(ForbiddenError):
        await interactor(ListReceiptsQuery(org_unit_id=foreign.id))

    assert reader.list_calls == []


async def test_transfer_journal_is_limited_to_scope_locations() -> None:
    own_unit, other_unit = uuid4(), uuid4()
    own = make_location_item(own_unit)
    other = make_location_item(other_unit)
    interactor, reader = build_list_transfers(
        scope=AccessScope.of([own_unit]), locations=[own, other]
    )

    await interactor(ListTransfersQuery())

    assert reader.list_calls == [
        {"org_unit_ids": [own.id], "limit": 20, "offset": 0, "search": None}
    ]


async def test_write_off_journal_returns_page() -> None:
    interactor, reader = build_list_write_offs()
    reader.items = [
        WriteOffListItem(
            id=uuid4(),
            org_unit_id=uuid4(),
            status="draft",
            occurred_at=OCCURRED_AT,
            posted_at=None,
            reason="Брак",
            line_count=3,
        )
    ]

    page = await interactor(ListWriteOffsQuery(limit=5))

    assert page.total == 1
    assert page.items[0].line_count == 3


async def test_unknown_receipt_raises_not_found() -> None:
    interactor, _, _ = build_get_receipt(None)

    with pytest.raises(ReceiptNotFoundError):
        await interactor(GetReceiptQuery(receipt_id=uuid4()))


async def test_unknown_transfer_raises_not_found() -> None:
    document_scope, _, _ = make_document_scope()
    interactor = GetTransferInteractor(
        transfer_reader=FakeTransferReader(),
        catalog_api=FakeCatalogAPI(),
        document_scope=document_scope,
    )

    with pytest.raises(TransferNotFoundError):
        await interactor(GetTransferQuery(transfer_id=uuid4()))


async def test_unknown_write_off_raises_not_found() -> None:
    document_scope, _, _ = make_document_scope()
    interactor = GetWriteOffInteractor(
        write_off_reader=FakeWriteOffReader(),
        catalog_api=FakeCatalogAPI(),
        document_scope=document_scope,
    )

    with pytest.raises(WriteOffNotFoundError):
        await interactor(GetWriteOffQuery(write_off_id=uuid4()))


async def test_receipt_card_checks_document_unit() -> None:
    unit = uuid4()
    detail = make_receipt_detail(uuid4(), org_unit_id=unit)
    interactor, reader, staff_api = build_get_receipt(detail)

    await interactor(GetReceiptQuery(receipt_id=detail.id))

    assert reader.get_calls == [detail.id]
    assert staff_api.can_calls == [(READ_DOCUMENTS, unit)]


async def test_receipt_card_denies_foreign_unit() -> None:
    detail = make_receipt_detail(uuid4(), org_unit_id=uuid4())
    interactor, reader, _ = build_get_receipt(detail, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(GetReceiptQuery(receipt_id=detail.id))

    assert reader.get_calls == [detail.id]


async def test_receipt_card_fills_nomenclature_names() -> None:
    nomenclature_id = uuid4()
    detail = make_receipt_detail(nomenclature_id, org_unit_id=uuid4())
    catalog_api = FakeCatalogAPI({nomenclature_id: "Говядина лопатка"})
    interactor, _, _ = build_get_receipt(detail, catalog_api=catalog_api)

    result = await interactor(GetReceiptQuery(receipt_id=detail.id))

    assert catalog_api.calls == [{nomenclature_id}]
    assert result.lines[0].nomenclature_name == "Говядина лопатка"


async def test_transfer_card_allows_destination_unit() -> None:
    from_unit, to_unit = uuid4(), uuid4()
    detail = make_transfer_detail(
        uuid4(), from_org_unit_id=from_unit, to_org_unit_id=to_unit
    )
    document_scope, _, staff_api = make_document_scope(allowed_units={to_unit})
    interactor = GetTransferInteractor(
        transfer_reader=FakeTransferReader(detail),
        catalog_api=FakeCatalogAPI(),
        document_scope=document_scope,
    )

    result = await interactor(GetTransferQuery(transfer_id=detail.id))

    assert result.id == detail.id
    assert staff_api.can_calls == [
        (READ_DOCUMENTS, from_unit),
        (READ_DOCUMENTS, to_unit),
    ]


async def test_transfer_card_denies_foreign_units() -> None:
    detail = make_transfer_detail(
        uuid4(), from_org_unit_id=uuid4(), to_org_unit_id=uuid4()
    )
    document_scope, _, _ = make_document_scope(allowed_units=set())

    interactor = GetTransferInteractor(
        transfer_reader=FakeTransferReader(detail),
        catalog_api=FakeCatalogAPI(),
        document_scope=document_scope,
    )

    with pytest.raises(ForbiddenError):
        await interactor(GetTransferQuery(transfer_id=detail.id))


async def test_write_off_card_fills_nomenclature_names() -> None:
    nomenclature_id = uuid4()
    detail = make_write_off_detail(nomenclature_id, org_unit_id=uuid4())
    catalog_api = FakeCatalogAPI({nomenclature_id: "Свинина шея"})
    document_scope, _, _ = make_document_scope()
    interactor = GetWriteOffInteractor(
        write_off_reader=FakeWriteOffReader(detail),
        catalog_api=catalog_api,
        document_scope=document_scope,
    )

    result = await interactor(GetWriteOffQuery(write_off_id=detail.id))

    assert result.lines[0].nomenclature_name == "Свинина шея"


async def test_receipt_journal_passes_search() -> None:
    interactor, reader = build_list_receipts()

    await interactor(ListReceiptsQuery(search="мясокомбинат"))

    assert reader.list_calls == [
        {"org_unit_ids": None, "limit": 20, "offset": 0, "search": "мясокомбинат"}
    ]
