"""Юнит-тесты чтения журнала документов склада."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.dto import (
    ReceiptDetail,
    ReceiptLineItem,
    ReceiptListItem,
    WriteOffDetail,
    WriteOffLineItem,
    WriteOffListItem,
)
from myasnaya_derevnya.modules.inventory.application.interactors.get_receipt import (
    GetReceiptInteractor,
    GetReceiptQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.get_write_off import (
    GetWriteOffInteractor,
    GetWriteOffQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.list_receipts import (
    ListReceiptsInteractor,
    ListReceiptsQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.list_write_offs import (
    ListWriteOffsInteractor,
    ListWriteOffsQuery,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    ReceiptNotFoundError,
    WriteOffNotFoundError,
)

OCCURRED_AT = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID) -> None:
        self._root_unit_id = root_unit_id

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeCatalogAPI:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}
        self.calls: list[set[UUID]] = []

    async def nomenclature_names(self, nomenclature_ids) -> dict[UUID, str]:
        self.calls.append(set(nomenclature_ids))
        return {key: self.names[key] for key in nomenclature_ids if key in self.names}


class FakeReceiptReader:
    def __init__(self) -> None:
        self.items: list[ReceiptListItem] = []
        self.detail: ReceiptDetail | None = None
        self.list_calls: list[dict] = []
        self.get_calls: list[UUID] = []

    async def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.items, len(self.items)

    async def get(self, receipt_id: UUID) -> ReceiptDetail | None:
        self.get_calls.append(receipt_id)
        return self.detail


class FakeWriteOffReader:
    def __init__(self) -> None:
        self.items: list[WriteOffListItem] = []
        self.detail: WriteOffDetail | None = None
        self.list_calls: list[dict] = []

    async def list(self, **kwargs):
        self.list_calls.append(kwargs)
        return self.items, len(self.items)

    async def get(self, write_off_id: UUID) -> WriteOffDetail | None:
        return self.detail


def make_receipt_detail(nomenclature_id: UUID) -> ReceiptDetail:
    return ReceiptDetail(
        id=uuid4(),
        warehouse_id=uuid4(),
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


def make_write_off_detail(nomenclature_id: UUID) -> WriteOffDetail:
    return WriteOffDetail(
        id=uuid4(),
        warehouse_id=uuid4(),
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


def build_list_receipts(*, allowed: bool = True):
    reader = FakeReceiptReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListReceiptsInteractor(
        identity_provider=FakeIdentityProvider(),
        receipt_reader=reader,
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=staff_api,
    )

    return interactor, reader


def build_list_write_offs():
    reader = FakeWriteOffReader()

    return (
        ListWriteOffsInteractor(
            identity_provider=FakeIdentityProvider(),
            write_off_reader=reader,
            business_api=FakeBusinessAPI(uuid4()),
            staff_api=FakeStaffAPI(),
        ),
        reader,
    )


async def test_journal_requires_read_permission() -> None:
    interactor, reader = build_list_receipts(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListReceiptsQuery())

    assert reader.list_calls == []


async def test_receipt_journal_passes_warehouse_filter_and_window() -> None:
    interactor, reader = build_list_receipts()
    warehouse_id = uuid4()

    page = await interactor(
        ListReceiptsQuery(warehouse_id=warehouse_id, limit=10, offset=20)
    )

    assert reader.list_calls == [
        {"warehouse_id": warehouse_id, "limit": 10, "offset": 20}
    ]
    assert (page.limit, page.offset, page.total) == (10, 20, 0)


async def test_write_off_journal_returns_page() -> None:
    interactor, reader = build_list_write_offs()
    reader.items = [
        WriteOffListItem(
            id=uuid4(),
            warehouse_id=uuid4(),
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
    reader = FakeReceiptReader()
    interactor = GetReceiptInteractor(
        identity_provider=FakeIdentityProvider(),
        receipt_reader=reader,
        catalog_api=FakeCatalogAPI(),
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=FakeStaffAPI(),
    )

    with pytest.raises(ReceiptNotFoundError):
        await interactor(GetReceiptQuery(receipt_id=uuid4()))


async def test_unknown_write_off_raises_not_found() -> None:
    interactor = GetWriteOffInteractor(
        identity_provider=FakeIdentityProvider(),
        write_off_reader=FakeWriteOffReader(),
        catalog_api=FakeCatalogAPI(),
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=FakeStaffAPI(),
    )

    with pytest.raises(WriteOffNotFoundError):
        await interactor(GetWriteOffQuery(write_off_id=uuid4()))


async def test_receipt_card_fills_nomenclature_names() -> None:
    nomenclature_id = uuid4()
    reader = FakeReceiptReader()
    reader.detail = make_receipt_detail(nomenclature_id)
    catalog_api = FakeCatalogAPI({nomenclature_id: "Говядина лопатка"})

    interactor = GetReceiptInteractor(
        identity_provider=FakeIdentityProvider(),
        receipt_reader=reader,
        catalog_api=catalog_api,
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=FakeStaffAPI(),
    )

    detail = await interactor(GetReceiptQuery(receipt_id=reader.detail.id))

    assert catalog_api.calls == [{nomenclature_id}]
    assert detail.lines[0].nomenclature_name == "Говядина лопатка"


async def test_write_off_card_fills_nomenclature_names() -> None:
    nomenclature_id = uuid4()
    reader = FakeWriteOffReader()
    reader.detail = make_write_off_detail(nomenclature_id)
    catalog_api = FakeCatalogAPI({nomenclature_id: "Свинина шея"})

    interactor = GetWriteOffInteractor(
        identity_provider=FakeIdentityProvider(),
        write_off_reader=reader,
        catalog_api=catalog_api,
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=FakeStaffAPI(),
    )

    detail = await interactor(GetWriteOffQuery(write_off_id=reader.detail.id))

    assert detail.lines[0].nomenclature_name == "Свинина шея"
