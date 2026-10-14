from uuid import UUID, uuid7

from myasnaya_derevnya.modules.catalog.domain.errors import EmptyNameError


class Category:
    def __init__(
        self,
        id_: UUID,
        name: str,
        parent_id: UUID | None,
        sort_order: int = 0,
    ) -> None:
        self._id = id_
        self._name = name
        self._parent_id = parent_id
        self._sort_order = sort_order

    @classmethod
    def create(
        cls,
        name: str,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> Category:
        if not name.strip():
            raise EmptyNameError()

        return cls(id_=uuid7(), name=name, parent_id=parent_id, sort_order=sort_order)

    def rename(self, name: str) -> None:
        self._name = name

    def change_sort_order(self, sort_order: int) -> None:
        self._sort_order = sort_order

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent_id(self) -> UUID | None:
        return self._parent_id

    @property
    def sort_order(self) -> int:
        return self._sort_order
