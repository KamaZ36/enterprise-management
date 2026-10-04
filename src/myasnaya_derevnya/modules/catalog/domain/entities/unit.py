from uuid import UUID, uuid7


class ProductUnit:
    def __init__(self, id: UUID, name: str, short_name: str) -> None:
        self._id = id
        self._name = name
        self._short_name = short_name

    @classmethod
    def create(cls, name: str, short_name: str) -> ProductUnit:
        return cls(id=uuid7(), name=name, short_name=short_name)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def short_name(self) -> str:
        return self.short_name
