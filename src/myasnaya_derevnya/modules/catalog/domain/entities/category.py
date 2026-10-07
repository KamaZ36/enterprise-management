from uuid import UUID, uuid7

from myasnaya_derevnya.modules.catalog.domain.errors import EmptyNameError


class Category:
    def __init__(self, id_: UUID, name: str, parent_id: UUID | None) -> None:
        self._id = id_
        self._name = name
        self._parent_id = parent_id

    @classmethod
    def create(cls, name: str, parent_id: UUID | None = None) -> Category:
        if not name.strip():
            raise EmptyNameError()

        return cls(id_=uuid7(), name=name, parent_id=parent_id)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent_id(self) -> UUID | None:
        return self._parent_id
