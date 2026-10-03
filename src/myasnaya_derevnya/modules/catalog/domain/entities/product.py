from uuid import UUID, uuid7


class Product:
    def __init__(self, id: UUID, sku: str, name: str, gtin: str | None) -> None:
        self._id = id
        self._sku = sku
        self._name = name
        self._gtin = gtin

    @classmethod
    def create(cls, sku: str, name: str, gtin: str | None) -> Product:
        return cls(id=uuid7(), sku=sku, name=name, gtin=gtin)
