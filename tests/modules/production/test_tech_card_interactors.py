from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.production.application.dto import (
    TechCardListItem,
    TechCardPage,
)
from myasnaya_derevnya.modules.production.application.interactors.create_tech_card import (
    CreateTechCardCommand,
    CreateTechCardInteractor,
    TechCardLineCommand,
)
from myasnaya_derevnya.modules.production.application.interactors.get_tech_card import (
    GetTechCardInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.list_tech_cards import (
    ListTechCardsInteractor,
    ListTechCardsQuery,
)
from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    InvalidTechCardLineError,
    TechCardNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import (
    MANAGE_TECH_CARDS,
    READ_TECH_CARDS,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
    SpecLineRole,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.utils import get_datetime_utc
from tests.modules.fakes import (
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeTransactionManager,
)


class FakeTechCardRepository:
    def __init__(self, *, version: int = 1, card: TechCard | None = None) -> None:
        self.version = version
        self.card = card
        self.added: list[TechCard] = []
        self.version_asked: list[str] = []

    async def next_version(self, code: str) -> int:
        self.version_asked.append(code)
        return self.version

    async def add(self, tech_card: TechCard) -> None:
        self.added.append(tech_card)

    async def get_by_id(self, tech_card_id):
        return self.card


class FakeTechCardReader:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.items: list[TechCardListItem] = []
        self.total = 0

    async def list(self, *, search, limit, offset):
        self.calls.append({"search": search, "limit": limit, "offset": offset})
        return self.items, self.total


class FakeCatalogAPI:
    def __init__(self, names: dict | None = None) -> None:
        self.names = names or {}
        self.asked: list[list] = []

    async def nomenclature_names(self, nomenclature_ids):
        self.asked.append(list(nomenclature_ids))
        return self.names


def sample_command() -> CreateTechCardCommand:
    return CreateTechCardCommand(
        code="PYTEST-SMOKE",
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=(
            TechCardLineCommand(
                role=SpecLineRole.COMPONENT,
                nomenclature_id=uuid4(),
                quantity=Decimal(100),
            ),
            TechCardLineCommand(
                role=SpecLineRole.OUTPUT,
                nomenclature_id=uuid4(),
                quantity=Decimal(80),
            ),
        ),
    )


def build_create(*, allowed: bool = True, version: int = 1):
    repository = FakeTechCardRepository(version=version)
    staff_api = FakeStaffAPI(allowed=allowed)
    transactions = FakeTransactionManager()
    interactor = CreateTechCardInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        tech_card_repository=repository,
        transaction_manager=transactions,
    )

    return interactor, repository, staff_api, transactions


async def test_create_requires_manage_permission() -> None:
    interactor, repository, _, _ = build_create(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(sample_command())

    assert repository.added == []


async def test_create_checks_manage_tech_cards_permission() -> None:
    interactor, _, staff_api, _ = build_create()

    await interactor(sample_command())

    assert staff_api.checked == [(MANAGE_TECH_CARDS.code, None)]


async def test_create_uses_repository_version_and_commits() -> None:
    interactor, repository, _, transactions = build_create(version=3)

    tech_card_id = await interactor(sample_command())

    assert repository.version_asked == ["PYTEST-SMOKE"]
    assert len(repository.added) == 1
    assert repository.added[0].version == 3
    assert repository.added[0].id == tech_card_id
    assert transactions.commits == 1


async def test_create_rejects_component_without_nomenclature() -> None:
    interactor, repository, _, _ = build_create()
    broken = CreateTechCardCommand(
        code="PYTEST-BROKEN",
        name="Сломанная",
        basis=TechCardBasis.INPUT,
        lines=(
            TechCardLineCommand(role=SpecLineRole.COMPONENT, quantity=Decimal(1)),
            TechCardLineCommand(
                role=SpecLineRole.OUTPUT,
                nomenclature_id=uuid4(),
                quantity=Decimal(1),
            ),
        ),
    )

    with pytest.raises(InvalidTechCardLineError):
        await interactor(broken)

    assert repository.added == []


async def test_create_rejects_loss_without_kind() -> None:
    interactor, repository, _, _ = build_create()
    broken = CreateTechCardCommand(
        code="PYTEST-BROKEN",
        name="Сломанная",
        basis=TechCardBasis.INPUT,
        lines=(
            TechCardLineCommand(role=SpecLineRole.LOSS, quantity=Decimal(1)),
            TechCardLineCommand(
                role=SpecLineRole.OUTPUT,
                nomenclature_id=uuid4(),
                quantity=Decimal(1),
            ),
        ),
    )

    with pytest.raises(InvalidTechCardLineError):
        await interactor(broken)

    assert repository.added == []


async def test_create_builds_loss_and_output_lines() -> None:
    interactor, repository, _, _ = build_create()
    command = CreateTechCardCommand(
        code="PYTEST-SMOKE",
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=(
            TechCardLineCommand(
                role=SpecLineRole.COMPONENT,
                nomenclature_id=uuid4(),
                quantity=Decimal(100),
            ),
            TechCardLineCommand(
                role=SpecLineRole.OUTPUT,
                nomenclature_id=uuid4(),
                quantity=Decimal(80),
                output_kind=OutputKind.MAIN,
            ),
            TechCardLineCommand(
                role=SpecLineRole.LOSS,
                loss_kind=LossKind.SHRINKAGE,
                quantity=Decimal(20),
            ),
        ),
    )

    await interactor(command)

    card = repository.added[0]
    assert len(card.losses) == 1
    assert card.losses[0].loss_kind is LossKind.SHRINKAGE
    assert card.main_output is not None


def build_get(*, allowed: bool = True, card: TechCard | None = None):
    repository = FakeTechCardRepository(card=card)
    staff_api = FakeStaffAPI(allowed=allowed)
    catalog_api = FakeCatalogAPI()
    interactor = GetTechCardInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        tech_card_repository=repository,
        catalog_api=catalog_api,
    )

    return interactor, staff_api, catalog_api


async def test_get_requires_read_permission() -> None:
    interactor, staff_api, _ = build_get(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(uuid4())

    assert staff_api.checked == [(READ_TECH_CARDS.code, None)]


async def test_get_unknown_card_raises_not_found() -> None:
    interactor, _, _ = build_get()

    with pytest.raises(TechCardNotFoundError):
        await interactor(uuid4())


async def test_get_attaches_nomenclature_names() -> None:
    component_id = uuid4()
    output_id = uuid4()
    card = TechCard.create(
        code="PYTEST-CARD",
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=[
            TechCardLine.component(nomenclature_id=component_id, quantity=Decimal(10)),
            TechCardLine.output(nomenclature_id=output_id, quantity=Decimal(8)),
        ],
    )
    interactor, _, catalog_api = build_get(card=card)
    catalog_api.names = {component_id: "Говядина", output_id: "Копчёная лопатка"}

    detail = await interactor(card.id)

    assert detail.id == card.id
    names = {line.nomenclature_name for line in detail.lines}
    assert names == {"Говядина", "Копчёная лопатка"}


def build_list(*, allowed: bool = True):
    reader = FakeTechCardReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListTechCardsInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=staff_api,
        tech_card_reader=reader,
    )

    return interactor, reader, staff_api


async def test_list_requires_read_permission() -> None:
    interactor, reader, _ = build_list(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListTechCardsQuery())

    assert reader.calls == []


async def test_list_strips_search_and_returns_page() -> None:
    interactor, reader, staff_api = build_list()
    item = TechCardListItem(
        id=uuid4(),
        code="PYTEST-CARD",
        version=1,
        name="Копчение",
        basis=TechCardBasis.INPUT,
        created_at=get_datetime_utc(),
        line_count=2,
    )
    reader.items = [item]
    reader.total = 1

    page = await interactor(ListTechCardsQuery(search="  копч  ", limit=5, offset=10))

    assert staff_api.checked == [(READ_TECH_CARDS.code, None)]
    assert reader.calls == [{"search": "копч", "limit": 5, "offset": 10}]
    assert isinstance(page, TechCardPage)
    assert page.items == [item]
    assert page.total == 1


async def test_list_blank_search_becomes_none() -> None:
    interactor, reader, _ = build_list()

    await interactor(ListTechCardsQuery(search="   "))

    assert reader.calls == [{"search": None, "limit": 50, "offset": 0}]
