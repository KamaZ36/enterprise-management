from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.dto import StopListItem
from myasnaya_derevnya.modules.catalog.application.errors import (
    NomenclatureNotFound,
    StopListItemNotFound,
    StopListLocationNotFound,
)
from myasnaya_derevnya.modules.catalog.application.interactors.add_stop_list_item import (
    AddStopListItemCommand,
    AddStopListItemInteractor,
)
from myasnaya_derevnya.modules.catalog.application.interactors.list_stop_list import (
    ListStopListInteractor,
    ListStopListQuery,
)
from myasnaya_derevnya.modules.catalog.application.interactors.remove_stop_list_item import (
    RemoveStopListItemCommand,
    RemoveStopListItemInteractor,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import (
    MANAGE_STOP_LIST,
    READ_STOP_LIST,
)
from tests.modules.fakes import (
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeStopListReader,
    FakeStopListRepository,
    FakeTransactionManager,
)


@dataclass
class FakeLocation:
    id: UUID


class FakeBusinessAPI:
    def __init__(self, location: FakeLocation | None) -> None:
        self.location = location

    async def stock_location(self, org_unit_id: UUID) -> FakeLocation | None:
        return self.location


class FakeNomenclatureRepository:
    def __init__(self, nomenclature: Nomenclature | None) -> None:
        self.nomenclature = nomenclature

    async def get_by_id(self, nomenclature_id: UUID) -> Nomenclature | None:
        if self.nomenclature is None or self.nomenclature.id != nomenclature_id:
            return None

        return self.nomenclature


def make_nomenclature() -> Nomenclature:
    return Nomenclature.create(
        sku="BEEF-001",
        name="Говядина",
        unit=UnitOfMeasurement.KG,
        category_id=uuid4(),
    )


def build_add(
    *,
    has_location: bool = True,
    nomenclature: Nomenclature | None = None,
    allowed: bool = True,
):
    location = FakeLocation(id=uuid4()) if has_location else None
    nomenclature = nomenclature if nomenclature is not None else make_nomenclature()
    staff_api = FakeStaffAPI(allowed=allowed)
    repository = FakeStopListRepository()
    transaction_manager = FakeTransactionManager()
    interactor = AddStopListItemInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(location),  # type: ignore[arg-type]
        staff_api=staff_api,  # type: ignore[arg-type]
        nomenclature_repository=FakeNomenclatureRepository(nomenclature),  # type: ignore[arg-type]
        stop_list_repository=repository,  # type: ignore[arg-type]
        transaction_manager=transaction_manager,  # type: ignore[arg-type]
    )

    return interactor, repository, staff_api, transaction_manager, location, nomenclature


async def test_add_stop_list_item_checks_permission_on_point() -> None:
    (
        interactor,
        repository,
        staff_api,
        transaction_manager,
        location,
        nomenclature,
    ) = build_add()

    await interactor(
        AddStopListItemCommand(
            org_unit_id=location.id,
            nomenclature_id=nomenclature.id,
        )
    )

    assert staff_api.checked == [(MANAGE_STOP_LIST.code, location.id)]
    assert len(repository.entries) == 1
    assert repository.entries[0].nomenclature_id == nomenclature.id
    assert repository.entries[0].org_unit_id == location.id
    assert transaction_manager.commits == 1


async def test_add_stop_list_item_requires_permission() -> None:
    interactor, repository, _, _, location, nomenclature = build_add(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(
            AddStopListItemCommand(
                org_unit_id=location.id,
                nomenclature_id=nomenclature.id,
            )
        )

    assert repository.entries == []


async def test_add_to_unknown_location_fails() -> None:
    interactor, repository, _, _, _, nomenclature = build_add(has_location=False)

    with pytest.raises(StopListLocationNotFound):
        await interactor(
            AddStopListItemCommand(
                org_unit_id=uuid4(),
                nomenclature_id=nomenclature.id,
            )
        )

    assert repository.entries == []


async def test_add_unknown_nomenclature_fails() -> None:
    interactor, repository, _, _, location, _ = build_add(
        nomenclature=make_nomenclature()
    )
    unknown_id = uuid4()

    with pytest.raises(NomenclatureNotFound):
        await interactor(
            AddStopListItemCommand(
                org_unit_id=location.id,
                nomenclature_id=unknown_id,
            )
        )

    assert repository.entries == []


def build_remove(*, removed: bool = True, allowed: bool = True):
    location = FakeLocation(id=uuid4())
    repository = FakeStopListRepository(removed=removed)
    transaction_manager = FakeTransactionManager()
    interactor = RemoveStopListItemInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(location),  # type: ignore[arg-type]
        staff_api=FakeStaffAPI(allowed=allowed),  # type: ignore[arg-type]
        stop_list_repository=repository,  # type: ignore[arg-type]
        transaction_manager=transaction_manager,  # type: ignore[arg-type]
    )

    return interactor, repository, transaction_manager, location


async def test_remove_stop_list_item() -> None:
    interactor, repository, transaction_manager, location = build_remove()
    nomenclature_id = uuid4()

    await interactor(
        RemoveStopListItemCommand(
            org_unit_id=location.id,
            nomenclature_id=nomenclature_id,
        )
    )

    assert repository.deleted == [(location.id, nomenclature_id)]
    assert transaction_manager.commits == 1


async def test_remove_missing_stop_list_item_fails() -> None:
    interactor, _, _, location = build_remove(removed=False)

    with pytest.raises(StopListItemNotFound):
        await interactor(
            RemoveStopListItemCommand(
                org_unit_id=location.id,
                nomenclature_id=uuid4(),
            )
        )


async def test_list_stop_list_requires_read_permission() -> None:
    location = FakeLocation(id=uuid4())
    item = StopListItem(
        nomenclature_id=uuid4(),
        nomenclature_name="Говядина",
        sku="BEEF-001",
        created_by=None,
        created_at=datetime.now(UTC),
    )
    reader = FakeStopListReader(items=[item])
    staff_api = FakeStaffAPI(allowed=True)
    interactor = ListStopListInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(location),  # type: ignore[arg-type]
        staff_api=staff_api,  # type: ignore[arg-type]
        stop_list_reader=reader,  # type: ignore[arg-type]
    )

    items = await interactor(ListStopListQuery(org_unit_id=location.id))

    assert items == [item]
    assert staff_api.checked == [(READ_STOP_LIST.code, location.id)]
