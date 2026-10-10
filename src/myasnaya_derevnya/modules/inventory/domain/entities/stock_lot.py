from datetime import date, datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import EmptyFieldError
from myasnaya_derevnya.utils import get_datetime_utc


class StockLot:
    """Партия номенклатуры: прослеживаемость и сроки годности.

    Себестоимость считается по средней на складе, поэтому у партии нет
    своей стоимости — только количество.
    """

    def __init__(
        self,
        id: UUID,
        nomenclature_id: UUID,
        lot_code: str,
        produced_at: date | None,
        expires_at: date | None,
        supplier_name: str | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._nomenclature_id = nomenclature_id
        self._lot_code = lot_code
        self._produced_at = produced_at
        self._expires_at = expires_at
        self._supplier_name = supplier_name
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        nomenclature_id: UUID,
        lot_code: str,
        produced_at: date | None = None,
        expires_at: date | None = None,
        supplier_name: str | None = None,
    ) -> StockLot:
        if not lot_code.strip():
            raise EmptyFieldError(field="lot_code")

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            produced_at=produced_at,
            expires_at=expires_at,
            supplier_name=supplier_name,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def lot_code(self) -> str:
        return self._lot_code

    @property
    def produced_at(self) -> date | None:
        return self._produced_at

    @property
    def expires_at(self) -> date | None:
        return self._expires_at

    @property
    def supplier_name(self) -> str | None:
        return self._supplier_name

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def is_expired(self, on: date) -> bool:
        if self._expires_at is None:
            return False
        return self._expires_at < on
