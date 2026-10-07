from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.category import Category


class CategoryRepository(ABC):
    @abstractmethod
    async def add(self, category: Category) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, category: Category) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, category_id: UUID) -> Category | None:
        raise NotImplementedError
