"""Юнит-тесты правки номенклатуры: правила, права, частичное обновление."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.errors import (
    CategoryNotFound,
    NomenclatureNotFound,
)
from myasnaya_derevnya.modules.catalog.application.interactors.update_nomenclature import (
    UpdateNomenclatureCommand,
    UpdateNomenclatureInteractor,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.errors import (
    EmptyNameError,
    NomenclatureInUseError,
)
from myasnaya_derevnya.modules.catalog.domain.services.nomenclature_changes import (
    NomenclatureChangesPolicy,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    async def get_root_unit_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeNomenclatureRepository:
    def __init__(self, nomenclature: Nomenclature | None) -> None:
        self.nomenclature = nomenclature
        self.saved: list[Nomenclature] = []

    async def get_by_id(self, nomenclature_id: UUID) -> Nomenclature | None:
        return self.nomenclature

    async def save(self, nomenclature: Nomenclature) -> None:
        self.saved.append(nomenclature)


class FakeCategoryRepository:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists

    async def check_exists_by_id(self, category_id: UUID) -> bool:
        return self.exists


class FakeNomenclatureUsage:
    def __init__(self, has_movements: bool = False) -> None:
        self.has_movements_value = has_movements
        self.calls: list[UUID] = []

    async def has_movements(self, nomenclature_id: UUID) -> bool:
        self.calls.append(nomenclature_id)
        return self.has_movements_value


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_nomenclature(
    *, unit: UnitOfMeasurement = UnitOfMeasurement.KG
) -> Nomenclature:
    return Nomenclature.create(
        sku="BEEF-SHOULDER",
        name="Говядина лопатка",
        unit=unit,
        type_=NomenclatureType.RAW_MATERIAL,
        category_id=uuid4(),
    )


def build(
    nomenclature: Nomenclature | None,
    *,
    allowed: bool = True,
    category_exists: bool = True,
    has_movements: bool = False,
):
    repository = FakeNomenclatureRepository(nomenclature)
    usage = FakeNomenclatureUsage(has_movements=has_movements)
    transaction_manager = FakeTransactionManager()
    interactor = UpdateNomenclatureInteractor(
        identity_provider=FakeIdentityProvider(),
        nomenclature_repository=repository,
        category_repository=FakeCategoryRepository(exists=category_exists),
        nomenclature_usage=usage,
        changes_policy=NomenclatureChangesPolicy(),
        business_api=FakeBusinessAPI(),
        staff_api=FakeStaffAPI(allowed=allowed),
        transaction_manager=transaction_manager,
    )

    return interactor, repository, usage, transaction_manager


async def test_requires_update_permission() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, _, _ = build(nomenclature, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(UpdateNomenclatureCommand(nomenclature_id=nomenclature.id))

    assert repository.saved == []


async def test_unknown_nomenclature_raises_not_found() -> None:
    interactor, repository, _, _ = build(None)

    with pytest.raises(NomenclatureNotFound):
        await interactor(UpdateNomenclatureCommand(nomenclature_id=uuid4()))

    assert repository.saved == []


async def test_rename_is_applied_and_saved() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, usage, transaction_manager = build(nomenclature)

    await interactor(
        UpdateNomenclatureCommand(nomenclature_id=nomenclature.id, name="  Новое имя ")
    )

    assert nomenclature.name == "Новое имя"
    assert repository.saved == [nomenclature]
    assert transaction_manager.commits == 1
    assert usage.calls == []


async def test_empty_name_is_rejected() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, _, _ = build(nomenclature)

    with pytest.raises(EmptyNameError):
        await interactor(
            UpdateNomenclatureCommand(nomenclature_id=nomenclature.id, name="   ")
        )

    assert repository.saved == []


async def test_unknown_category_is_rejected() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, _, _ = build(nomenclature, category_exists=False)

    with pytest.raises(CategoryNotFound):
        await interactor(
            UpdateNomenclatureCommand(
                nomenclature_id=nomenclature.id, category_id=uuid4()
            )
        )

    assert repository.saved == []


async def test_unit_can_change_while_there_are_no_movements() -> None:
    nomenclature = make_nomenclature()
    interactor, _, usage, _ = build(nomenclature, has_movements=False)

    await interactor(
        UpdateNomenclatureCommand(
            nomenclature_id=nomenclature.id, unit=UnitOfMeasurement.PIECE
        )
    )

    assert nomenclature.unit is UnitOfMeasurement.PIECE
    assert usage.calls == [nomenclature.id]


async def test_unit_cannot_change_after_movements() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, _, _ = build(nomenclature, has_movements=True)

    with pytest.raises(NomenclatureInUseError) as error:
        await interactor(
            UpdateNomenclatureCommand(
                nomenclature_id=nomenclature.id, unit=UnitOfMeasurement.PIECE
            )
        )

    assert error.value.field == "единица измерения"
    assert nomenclature.unit is UnitOfMeasurement.KG
    assert repository.saved == []


async def test_same_unit_is_not_treated_as_a_change() -> None:
    nomenclature = make_nomenclature()
    interactor, repository, _, _ = build(nomenclature, has_movements=True)

    await interactor(
        UpdateNomenclatureCommand(
            nomenclature_id=nomenclature.id, unit=UnitOfMeasurement.KG
        )
    )

    assert repository.saved == [nomenclature]


async def test_deactivate_and_activate() -> None:
    nomenclature = make_nomenclature()
    interactor, _, _, _ = build(nomenclature)

    await interactor(
        UpdateNomenclatureCommand(nomenclature_id=nomenclature.id, is_active=False)
    )
    assert nomenclature.is_active is False

    await interactor(
        UpdateNomenclatureCommand(nomenclature_id=nomenclature.id, is_active=True)
    )
    assert nomenclature.is_active is True
