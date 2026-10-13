from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.errors import NomenclatureInUseError


class NomenclatureChangesPolicy:
    def ensure_changeable(
        self,
        *,
        nomenclature_id: UUID,
        current_unit: UnitOfMeasurement,
        new_unit: UnitOfMeasurement | None,
        current_type: NomenclatureType,
        new_type: NomenclatureType | None,
        has_movements: bool,
    ) -> None:
        if not has_movements:
            return

        if new_unit is not None and new_unit is not current_unit:
            raise NomenclatureInUseError(
                nomenclature_id=nomenclature_id,
                field="единица измерения",
            )

        if new_type is not None and new_type is not current_type:
            raise NomenclatureInUseError(
                nomenclature_id=nomenclature_id,
                field="тип номенклатуры",
            )
