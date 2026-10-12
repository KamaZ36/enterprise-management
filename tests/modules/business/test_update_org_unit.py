from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.business.application.errors import OrgUnitNotFound
from myasnaya_derevnya.modules.business.application.interactors.update_org_unit import (
    UpdateOrgUnitCommand,
    UpdateOrgUnitInteractor,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnit,
    OrgUnitType,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[str] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append(permission.code)
        return self.allowed


class FakeOrgUnitRepository:
    def __init__(self, org_unit: OrgUnit | None) -> None:
        self.org_unit = org_unit
        self.saved: list[OrgUnit] = []

    async def get_by_id(self, org_unit_id: UUID) -> OrgUnit | None:
        return self.org_unit

    async def get_root_id(self) -> UUID | None:
        return uuid4()

    async def save(self, org_unit: OrgUnit) -> None:
        self.saved.append(org_unit)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_org_unit() -> OrgUnit:
    return OrgUnit.create_child(
        parent_id=uuid4(),
        type=OrgUnitType.CAFE,
        code="CAFE-01",
        name="Кафе на Ленина",
        address="ул. Ленина, 1",
        phone_number=PhoneNumber.parse("+79001112233"),
    )


def build(org_unit: OrgUnit | None, *, allowed: bool = True):
    repository = FakeOrgUnitRepository(org_unit)
    transaction_manager = FakeTransactionManager()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = UpdateOrgUnitInteractor(
        identity_provider=FakeIdentityProvider(),
        org_unit_repository=repository,
        transaction_manager=transaction_manager,
        staff_api=staff_api,
    )

    return interactor, repository, transaction_manager, staff_api


async def test_requires_update_permission() -> None:
    unit = make_org_unit()
    interactor, repository, _, staff_api = build(unit, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateOrgUnitCommand(unit.id, provided=frozenset({"name"}), name="Другое")
        )

    assert repository.saved == []
    assert staff_api.checked == ["org_unit.update"]


async def test_unknown_org_unit_raises_not_found() -> None:
    interactor, _, _, _ = build(None)

    with pytest.raises(OrgUnitNotFound):
        await interactor(UpdateOrgUnitCommand(uuid4(), provided=frozenset()))


async def test_rename_is_applied() -> None:
    unit = make_org_unit()
    interactor, repository, transaction_manager, _ = build(unit)

    await interactor(
        UpdateOrgUnitCommand(unit.id, provided=frozenset({"name"}), name="Кафе на Мира")
    )

    assert unit.name == "Кафе на Мира"
    assert repository.saved == [unit]
    assert transaction_manager.commits == 1


async def test_contacts_are_changed_and_phone_cleared() -> None:
    unit = make_org_unit()
    interactor, _, _, _ = build(unit)

    await interactor(
        UpdateOrgUnitCommand(
            unit.id,
            provided=frozenset({"address", "phone_number"}),
            address="ул. Мира, 5",
            phone_number=None,
        )
    )

    assert unit.address == "ул. Мира, 5"
    assert unit.phone_number is None


async def test_address_change_keeps_phone() -> None:
    unit = make_org_unit()
    interactor, _, _, _ = build(unit)

    await interactor(
        UpdateOrgUnitCommand(
            unit.id, provided=frozenset({"address"}), address="ул. Мира, 5"
        )
    )

    assert unit.phone_number is not None


async def test_deactivate_and_activate() -> None:
    unit = make_org_unit()
    interactor, _, _, _ = build(unit)

    await interactor(
        UpdateOrgUnitCommand(unit.id, provided=frozenset(), is_active=False)
    )
    assert unit.is_active is False

    await interactor(
        UpdateOrgUnitCommand(unit.id, provided=frozenset(), is_active=True)
    )
    assert unit.is_active is True
