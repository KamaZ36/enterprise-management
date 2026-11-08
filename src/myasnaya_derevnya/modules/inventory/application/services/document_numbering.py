from datetime import datetime

from myasnaya_derevnya.core.timezone import company_date
from myasnaya_derevnya.modules.inventory.domain.errors import TimezoneRequiredError
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_number import (
    DocumentNumber,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.document_number.base import (
    DocumentNumberRepository,
)


async def next_document_number(
    repository: DocumentNumberRepository,
    document_type: DocumentType,
    occurred_at: datetime,
) -> str:
    """Выдаёт следующий номер документа в сквозной нумерации компании."""

    if occurred_at.tzinfo is None:
        raise TimezoneRequiredError(field="occurred_at")

    year = company_date(occurred_at).year
    sequence = await repository.next_sequence(document_type, year)

    return DocumentNumber.create(document_type, year, sequence).value
