from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.interactors.get_price_list_binding import (
    GetPriceListBindingInteractor,
    GetPriceListBindingQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_PRICE_LIST


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed

    async def can_anywhere(self, *, user_id: UUID, permission: object) -> bool:
        return await self.can(user_id=user_id, permission=permission, org_unit_id=None)


class FakeBindingRepository:
    def __init__(self, binding: PriceListBinding | None) -> None:
        self.binding = binding
        self.calls: list[UUID] = []

    async def get_by_org_unit(self, org_unit_id: UUID) -> PriceListBinding | None:
        self.calls.append(org_unit_id)
        return self.binding


def build(
    binding: PriceListBinding | None, *, allowed: bool = True
) -> tuple[GetPriceListBindingInteractor, FakeBindingRepository, FakeStaffAPI]:
    repository = FakeBindingRepository(binding)
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = GetPriceListBindingInteractor(
        identity_provider=FakeIdentityProvider(),
        binding_repository=repository,  # type: ignore[arg-type]
        staff_api=staff_api,  # type: ignore[arg-type]
    )
    return interactor, repository, staff_api


async def test_point_without_price_list_returns_none() -> None:
    interactor, repository, _ = build(None)
    org_unit_id = uuid4()

    result = await interactor(GetPriceListBindingQuery(org_unit_id=org_unit_id))

    assert result is None
    assert repository.calls == [org_unit_id]


async def test_point_binding_is_returned() -> None:
    binding = PriceListBinding.create(org_unit_id=uuid4(), price_list_id=uuid4())
    interactor, repository, _ = build(binding)

    result = await interactor(GetPriceListBindingQuery(org_unit_id=binding.org_unit_id))

    assert result is not None
    assert result.org_unit_id == binding.org_unit_id
    assert result.price_list_id == binding.price_list_id
    assert repository.calls == [binding.org_unit_id]


async def test_reading_binding_requires_permission() -> None:
    interactor, repository, staff_api = build(None, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(GetPriceListBindingQuery(org_unit_id=uuid4()))

    assert staff_api.checked == [(READ_PRICE_LIST.code, None)]
    assert repository.calls == []
