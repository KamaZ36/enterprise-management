from datetime import UTC, datetime

import pytest

from myasnaya_derevnya.modules.inventory.application.services.document_numbering import (
    next_document_number,
)
from myasnaya_derevnya.modules.inventory.domain.errors import TimezoneRequiredError
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_number import (
    DocumentNumber,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)


@pytest.mark.parametrize(
    ("document_type", "expected"),
    [
        (DocumentType.RECEIPT, "ПН-2026-000123"),
        (DocumentType.WRITE_OFF, "СП-2026-000123"),
        (DocumentType.TRANSFER, "ПМ-2026-000123"),
        (DocumentType.INVENTORY_COUNT, "ИНВ-2026-000123"),
    ],
)
def test_document_number_format(
    document_type: DocumentType, expected: str
) -> None:
    number = DocumentNumber.create(document_type, year=2026, sequence=123)

    assert number.value == expected


def test_document_number_pads_sequence_to_six_digits() -> None:
    number = DocumentNumber.create(DocumentType.RECEIPT, year=2026, sequence=7)

    assert number.value == "ПН-2026-000007"


class FakeDocumentNumberRepository:
    def __init__(self, sequences: dict[str, int] | None = None) -> None:
        self._sequences = sequences or {}
        self.calls: list[tuple[DocumentType, int]] = []

    async def next_sequence(
        self, document_type: DocumentType, year: int
    ) -> int:
        self.calls.append((document_type, year))
        key = f"{document_type.value}:{year}"
        self._sequences[key] = self._sequences.get(key, 0) + 1

        return self._sequences[key]


async def test_next_document_number_uses_company_year() -> None:
    repository = FakeDocumentNumberRepository()

    # 31 декабря 22:30 UTC — уже 1 января в Москве.
    number = await next_document_number(
        repository,
        DocumentType.RECEIPT,
        datetime(2025, 12, 31, 22, 30, tzinfo=UTC),
    )

    assert number == "ПН-2026-000001"
    assert repository.calls == [(DocumentType.RECEIPT, 2026)]


async def test_next_document_number_requires_timezone() -> None:
    repository = FakeDocumentNumberRepository()

    with pytest.raises(TimezoneRequiredError):
        await next_document_number(
            repository,
            DocumentType.RECEIPT,
            datetime(2026, 1, 1, 12, 0),
        )

    assert repository.calls == []
