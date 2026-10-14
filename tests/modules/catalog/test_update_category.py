from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.errors import (
    CategoryAlreadyExists,
    CategoryNotFound,
)
from myasnaya_derevnya.modules.catalog.application.interactors.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryInteractor,
)
from myasnaya_derevnya.modules.catalog.domain.entities.category import Category


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

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        return self.allowed

    async def can_anywhere(self, *, user_id: UUID, permission: object) -> bool:
        return await self.can(user_id=user_id, permission=permission, org_unit_id=None)


class FakeCategoryRepository:
    def __init__(self, category: Category | None, *, name_taken: bool = False) -> None:
        self.category = category
        self.name_taken = name_taken
        self.saved: list[Category] = []
        self.name_checks: list[str] = []

    async def get_by_id(self, category_id: UUID) -> Category | None:
        return self.category

    async def check_exists_by_name(self, category_name: str) -> bool:
        self.name_checks.append(category_name)
        return self.name_taken

    async def save(self, category: Category) -> None:
        self.saved.append(category)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def build(category: Category | None, *, allowed: bool = True, name_taken: bool = False):
    repository = FakeCategoryRepository(category, name_taken=name_taken)
    transaction_manager = FakeTransactionManager()
    interactor = UpdateCategoryInteractor(
        identity_provider=FakeIdentityProvider(),
        category_repository=repository,
        transaction_manager=transaction_manager,
        business_api=FakeBusinessAPI(),
        staff_api=FakeStaffAPI(allowed=allowed),
    )

    return interactor, repository, transaction_manager


async def test_requires_update_permission() -> None:
    category = Category.create(name="Мясо")
    interactor, repository, _ = build(category, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(UpdateCategoryCommand(category.id, "Мясо и птица"))

    assert repository.saved == []


async def test_unknown_category_raises_not_found() -> None:
    interactor, _, _ = build(None)

    with pytest.raises(CategoryNotFound):
        await interactor(UpdateCategoryCommand(uuid4(), "Мясо"))


async def test_rename_is_applied() -> None:
    category = Category.create(name="Мясо")
    interactor, repository, transaction_manager = build(category)

    await interactor(UpdateCategoryCommand(category.id, "  Мясо и птица  "))

    assert category.name == "Мясо и птица"
    assert repository.saved == [category]
    assert repository.name_checks == ["Мясо и птица"]
    assert transaction_manager.commits == 1


async def test_same_name_changes_nothing() -> None:
    category = Category.create(name="Мясо")
    interactor, repository, transaction_manager = build(category)

    await interactor(UpdateCategoryCommand(category.id, "Мясо"))

    assert repository.saved == []
    assert repository.name_checks == []
    assert transaction_manager.commits == 0


async def test_duplicate_name_is_rejected() -> None:
    category = Category.create(name="Мясо")
    interactor, repository, _ = build(category, name_taken=True)

    with pytest.raises(CategoryAlreadyExists):
        await interactor(UpdateCategoryCommand(category.id, "Рыба"))

    assert category.name == "Мясо"
    assert repository.saved == []
