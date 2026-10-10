from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.catalog.application.dto import CategoryListItem


class CategoryReader(ABC):
    """Чтение категорий для интерфейса: плоские DTO вместо доменных сущностей."""

    @abstractmethod
    async def list(self, *, search: str | None = None) -> list[CategoryListItem]:
        raise NotImplementedError
