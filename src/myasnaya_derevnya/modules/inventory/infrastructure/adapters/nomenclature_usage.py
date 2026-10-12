from uuid import UUID

from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)


class InventoryNomenclatureUsage:
    def __init__(self, movement_repository: StockMovementRepository) -> None:
        self._movement_repository = movement_repository

    async def has_movements(self, nomenclature_id: UUID) -> bool:
        return (
            await self._movement_repository.count_for_nomenclature(nomenclature_id) > 0
        )
