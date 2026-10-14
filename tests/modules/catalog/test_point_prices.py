
from uuid import uuid4

from myasnaya_derevnya.modules.catalog.application.interactors.get_point_prices import (
    GetPointPricesInteractor,
    GetPointPricesQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)


class FakeBindingRepository:
    def __init__(self, binding: PriceListBinding | None) -> None:
        self._binding = binding

    async def get_by_org_unit(self, org_unit_id):
        return self._binding


class FakePriceRepository:
    def __init__(self, values: dict) -> None:
        self._values = values
        self.calls: list[tuple[list, object]] = []

    async def get_values_by_nomenclatures_and_list(
        self, nomenclature_ids, price_list_id
    ):
        ids = list(nomenclature_ids)
        self.calls.append((ids, price_list_id))

        return {nid: self._values[nid] for nid in ids if nid in self._values}


async def test_point_prices_are_fetched_in_one_batch() -> None:
    price_list_id = uuid4()
    first, second = uuid4(), uuid4()
    price_repository = FakePriceRepository({first: 1000, second: 2500})
    binding = PriceListBinding.create(org_unit_id=uuid4(), price_list_id=price_list_id)

    interactor = GetPointPricesInteractor(
        binding_repository=FakeBindingRepository(binding),  # type: ignore[arg-type]
        price_repository=price_repository,  # type: ignore[arg-type]
    )

    prices = await interactor(
        GetPointPricesQuery(org_unit_id=uuid4(), nomenclature_ids=[first, second])
    )

    assert prices == {first: 1000, second: 2500}
    assert price_repository.calls == [([first, second], price_list_id)]


async def test_point_without_binding_has_no_prices() -> None:
    price_repository = FakePriceRepository({})

    interactor = GetPointPricesInteractor(
        binding_repository=FakeBindingRepository(None),  # type: ignore[arg-type]
        price_repository=price_repository,  # type: ignore[arg-type]
    )

    prices = await interactor(
        GetPointPricesQuery(org_unit_id=uuid4(), nomenclature_ids=[uuid4()])
    )

    assert prices == {}
    assert price_repository.calls == []
