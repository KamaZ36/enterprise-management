from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot import StockLot
from myasnaya_derevnya.modules.inventory.domain.errors import StockLotNotFoundError
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.base import (
    StockLotRepository,
)


class LotResolver:
    """Разбор партий по коду.

    Поступление может завести партию, списание — только найти существующую.
    """

    def __init__(self, lot_repository: StockLotRepository) -> None:
        self._lot_repository = lot_repository

    async def find_or_create(
        self,
        *,
        nomenclature_id: UUID,
        lot_code: str | None,
        expires_at: date | None = None,
        supplier_name: str | None = None,
    ) -> UUID | None:
        if not lot_code:
            return None

        existing = await self._lot_repository.get_by_code(nomenclature_id, lot_code)
        if existing is not None:
            return existing.id

        lot = StockLot.create(
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            expires_at=expires_at,
            supplier_name=supplier_name,
        )
        await self._lot_repository.add(lot)

        return lot.id

    async def require(self, *, nomenclature_id: UUID, lot_code: str) -> UUID:
        existing = await self._lot_repository.get_by_code(nomenclature_id, lot_code)
        if existing is None:
            raise StockLotNotFoundError(
                nomenclature_id=nomenclature_id, lot_code=lot_code
            )

        return existing.id
