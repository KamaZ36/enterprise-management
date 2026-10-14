from uuid import UUID, uuid4

from myasnaya_derevnya.modules.catalog.application.dto import AssortmentItem
from myasnaya_derevnya.modules.catalog.application.interactors.get_point_assortment import (
    GetPointAssortmentInteractor,
    GetPointAssortmentQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)


class FakeBindingRepository:
    def __init__(self, binding: PriceListBinding | None) -> None:
        self.binding = binding
        self.calls: list[UUID] = []

    async def get_by_org_unit(self, org_unit_id: UUID) -> PriceListBinding | None:
        self.calls.append(org_unit_id)
        return self.binding


class FakeReader:
    def __init__(self, items: list[AssortmentItem]) -> None:
        self.items = items
        self.calls: list[UUID] = []

    async def list_assortment(self, price_list_id: UUID) -> list[AssortmentItem]:
        self.calls.append(price_list_id)
        return self.items


def make_item() -> AssortmentItem:
    return AssortmentItem(
        nomenclature_id=uuid4(),
        name="Говядина лопатка",
        sku="BEEF-001",
        unit=UnitOfMeasurement.KG,
        value=44300,
    )


async def test_point_without_price_list_sells_nothing() -> None:
    reader = FakeReader([])
    interactor = GetPointAssortmentInteractor(
        binding_repository=FakeBindingRepository(None),  # type: ignore[arg-type]
        reader=reader,  # type: ignore[arg-type]
    )

    items = await interactor(GetPointAssortmentQuery(org_unit_id=uuid4()))

    assert items == []
    assert reader.calls == []


async def test_point_assortment_comes_from_bound_price_list() -> None:
    price_list_id = uuid4()
    binding = PriceListBinding.create(org_unit_id=uuid4(), price_list_id=price_list_id)
    item = make_item()
    bindings = FakeBindingRepository(binding)
    reader = FakeReader([item])
    interactor = GetPointAssortmentInteractor(
        binding_repository=bindings,  # type: ignore[arg-type]
        reader=reader,  # type: ignore[arg-type]
    )

    items = await interactor(
        GetPointAssortmentQuery(org_unit_id=binding.org_unit_id)
    )

    assert items == [item]
    assert reader.calls == [price_list_id]
    assert bindings.calls == [binding.org_unit_id]
