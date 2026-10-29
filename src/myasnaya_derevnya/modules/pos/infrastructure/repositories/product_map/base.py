from abc import ABC, abstractmethod
from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)


class PosProductMapRepository(ABC):
    @abstractmethod
    async def get_by_id(self, mapping_id: UUID) -> PosProductMapping | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_source_product(
        self, source_id: UUID, doka_product_guid: str
    ) -> PosProductMapping | None:
        raise NotImplementedError

    @abstractmethod
    async def mappings_for(
        self, source_id: UUID, product_guids: Iterable[str]
    ) -> dict[str, PosProductMapping]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_source(
        self, source_id: UUID, *, search: str | None = None
    ) -> list[PosProductMapping]:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, mapping: PosProductMapping) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, mapping_id: UUID) -> None:
        raise NotImplementedError
