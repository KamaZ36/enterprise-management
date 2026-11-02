from datetime import date
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot import StockLot
from myasnaya_derevnya.modules.inventory.domain.errors import (
    AmbiguousLotCodeError,
    EmptyFieldError,
    LotNomenclatureMismatchError,
    StockLotNotFoundByIdError,
    StockLotNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.base import (
    StockLotRepository,
)


class LotResolver:
    def __init__(self, lot_repository: StockLotRepository) -> None:
        self._lot_repository = lot_repository

    async def find_or_create(
        self,
        *,
        nomenclature_id: UUID,
        lot_code: str | None,
        produced_at: date | None = None,
        expires_at: date | None = None,
        supplier_name: str | None = None,
        origin_org_unit_id: UUID | None = None,
        vetis_vsd_number: str | None = None,
        vetis_vsd_guid: UUID | None = None,
        vetis_batch_id: str | None = None,
        vetis_product_item_guid: UUID | None = None,
        vetis_entered_by: UUID | None = None,
        veterinary_document_id: UUID | None = None,
    ) -> UUID | None:
        if not lot_code:
            if _has_vetis(
                vetis_vsd_number,
                vetis_vsd_guid,
                vetis_batch_id,
                vetis_product_item_guid,
                veterinary_document_id,
            ):
                raise EmptyFieldError(field="lot_code")
            return None

        existing = await self._lot_repository.get_by_identity(
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            produced_at=produced_at,
            supplier_name=supplier_name,
        )
        if existing is not None:
            if _has_vetis(
                vetis_vsd_number,
                vetis_vsd_guid,
                vetis_batch_id,
                vetis_product_item_guid,
                veterinary_document_id,
            ):
                existing.attach_vetis(
                    vsd_number=vetis_vsd_number,
                    vsd_guid=vetis_vsd_guid,
                    batch_id=vetis_batch_id,
                    product_item_guid=vetis_product_item_guid,
                    entered_by=vetis_entered_by,
                    veterinary_document_id=veterinary_document_id,
                )
                await self._lot_repository.save(existing)
            return existing.id

        lot = StockLot.create(
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            produced_at=produced_at,
            expires_at=expires_at,
            supplier_name=supplier_name,
            origin_org_unit_id=origin_org_unit_id,
            vetis_vsd_number=vetis_vsd_number,
            vetis_vsd_guid=vetis_vsd_guid,
            vetis_batch_id=vetis_batch_id,
            vetis_product_item_guid=vetis_product_item_guid,
            vetis_entered_by=vetis_entered_by,
            veterinary_document_id=veterinary_document_id,
        )
        await self._lot_repository.add(lot)

        return lot.id

    async def get_existing(
        self,
        *,
        nomenclature_id: UUID,
        lot_code: str | None,
        produced_at: date | None = None,
        supplier_name: str | None = None,
    ) -> StockLot | None:
        if not lot_code:
            return None

        return await self._lot_repository.get_by_identity(
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            produced_at=produced_at,
            supplier_name=supplier_name,
        )

    async def get(self, lot_id: UUID) -> StockLot | None:
        return await self._lot_repository.get_by_id(lot_id)

    async def ensure_matches(
        self, *, nomenclature_id: UUID, lot_id: UUID
    ) -> None:
        """Проверяет, что партия существует и относится к номенклатуре."""
        lot = await self._lot_repository.get_by_id(lot_id)
        if lot is None:
            raise StockLotNotFoundByIdError(lot_id)
        if lot.nomenclature_id != nomenclature_id:
            raise LotNomenclatureMismatchError(
                lot_id=lot_id, nomenclature_id=nomenclature_id
            )

    async def attach_vetis(
        self,
        *,
        nomenclature_id: UUID,
        lot_id: UUID,
        vetis_vsd_number: str | None = None,
        vetis_vsd_guid: UUID | None = None,
        vetis_batch_id: str | None = None,
        vetis_product_item_guid: UUID | None = None,
        vetis_entered_by: UUID | None = None,
        veterinary_document_id: UUID | None = None,
    ) -> None:
        if not _has_vetis(
            vetis_vsd_number,
            vetis_vsd_guid,
            vetis_batch_id,
            vetis_product_item_guid,
            veterinary_document_id,
        ):
            return

        lot = await self._lot_repository.get_by_id(lot_id)
        if lot is None:
            raise StockLotNotFoundByIdError(lot_id)
        if lot.nomenclature_id != nomenclature_id:
            raise LotNomenclatureMismatchError(
                lot_id=lot_id, nomenclature_id=nomenclature_id
            )

        lot.attach_vetis(
            vsd_number=vetis_vsd_number,
            vsd_guid=vetis_vsd_guid,
            batch_id=vetis_batch_id,
            product_item_guid=vetis_product_item_guid,
            entered_by=vetis_entered_by,
            veterinary_document_id=veterinary_document_id,
        )
        await self._lot_repository.save(lot)

    async def require(self, *, nomenclature_id: UUID, lot_code: str) -> UUID:
        matches = await self._lot_repository.list_by_code(nomenclature_id, lot_code)
        if not matches:
            raise StockLotNotFoundError(
                nomenclature_id=nomenclature_id, lot_code=lot_code
            )
        if len(matches) > 1:
            raise AmbiguousLotCodeError(
                nomenclature_id=nomenclature_id, lot_code=lot_code
            )

        return matches[0].id


def _has_vetis(*values: object | None) -> bool:
    return any(value is not None for value in values)
