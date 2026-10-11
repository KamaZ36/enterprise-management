from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    NomenclatureNotAllowedInWarehouseError,
)

ALLOWED_NOMENCLATURE_TYPES: dict[WarehouseType, frozenset[str]] = {
    WarehouseType.RAW: frozenset({"raw_material"}),
    WarehouseType.PRODUCTION: frozenset({"raw_material", "semi_finished"}),
    WarehouseType.FINISHED: frozenset({"semi_finished", "finished_good"}),
    WarehouseType.SHOP: frozenset({"finished_good"}),
}


class WarehousePurposePolicy:
    def allows(
        self, warehouse_type: WarehouseType, nomenclature_type_code: str
    ) -> bool:
        return nomenclature_type_code in ALLOWED_NOMENCLATURE_TYPES[warehouse_type]

    def ensure_allowed(
        self,
        *,
        warehouse: Warehouse,
        nomenclature_id: UUID,
        nomenclature_type_code: str,
    ) -> None:
        if not self.allows(warehouse.type, nomenclature_type_code):
            raise NomenclatureNotAllowedInWarehouseError(
                warehouse_id=warehouse.id,
                nomenclature_id=nomenclature_id,
                warehouse_type=warehouse.type.value,
                nomenclature_type=nomenclature_type_code,
            )
