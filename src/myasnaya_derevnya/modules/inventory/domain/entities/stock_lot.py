from datetime import date, datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyFieldError,
    LotVeterinaryDocumentConflictError,
    LotVetisConflictError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class StockLot:
    def __init__(
        self,
        id: UUID,
        nomenclature_id: UUID,
        lot_code: str,
        produced_at: date | None,
        expires_at: date | None,
        supplier_name: str | None,
        created_at: datetime,
        origin_org_unit_id: UUID | None = None,
        vetis_vsd_number: str | None = None,
        vetis_vsd_guid: UUID | None = None,
        vetis_batch_id: str | None = None,
        vetis_product_item_guid: UUID | None = None,
        vetis_entered_at: datetime | None = None,
        vetis_entered_by: UUID | None = None,
        veterinary_document_id: UUID | None = None,
    ) -> None:
        self._id = id
        self._nomenclature_id = nomenclature_id
        self._lot_code = lot_code
        self._produced_at = produced_at
        self._expires_at = expires_at
        self._supplier_name = supplier_name
        self._origin_org_unit_id = origin_org_unit_id
        self._created_at = created_at
        self._vetis_vsd_number = vetis_vsd_number
        self._vetis_vsd_guid = vetis_vsd_guid
        self._vetis_batch_id = vetis_batch_id
        self._vetis_product_item_guid = vetis_product_item_guid
        self._vetis_entered_at = vetis_entered_at
        self._vetis_entered_by = vetis_entered_by
        self._veterinary_document_id = veterinary_document_id

    @classmethod
    def create(
        cls,
        nomenclature_id: UUID,
        lot_code: str,
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
    ) -> StockLot:
        if not lot_code.strip():
            raise EmptyFieldError(field="lot_code")

        has_vetis = any(
            value is not None
            for value in (
                vetis_vsd_number,
                vetis_vsd_guid,
                vetis_batch_id,
                vetis_product_item_guid,
            )
        )

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            lot_code=lot_code,
            produced_at=produced_at,
            expires_at=expires_at,
            supplier_name=supplier_name,
            origin_org_unit_id=origin_org_unit_id,
            created_at=get_datetime_utc(),
            vetis_vsd_number=vetis_vsd_number,
            vetis_vsd_guid=vetis_vsd_guid,
            vetis_batch_id=vetis_batch_id,
            vetis_product_item_guid=vetis_product_item_guid,
            vetis_entered_at=get_datetime_utc() if has_vetis else None,
            vetis_entered_by=vetis_entered_by,
            veterinary_document_id=veterinary_document_id,
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
    def origin_org_unit_id(self) -> UUID | None:
        return self._origin_org_unit_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def vetis_vsd_number(self) -> str | None:
        return self._vetis_vsd_number

    @property
    def vetis_vsd_guid(self) -> UUID | None:
        return self._vetis_vsd_guid

    @property
    def vetis_batch_id(self) -> str | None:
        return self._vetis_batch_id

    @property
    def vetis_product_item_guid(self) -> UUID | None:
        return self._vetis_product_item_guid

    @property
    def vetis_entered_at(self) -> datetime | None:
        return self._vetis_entered_at

    @property
    def vetis_entered_by(self) -> UUID | None:
        return self._vetis_entered_by

    @property
    def veterinary_document_id(self) -> UUID | None:
        return self._veterinary_document_id

    def attach_vetis(
        self,
        *,
        vsd_number: str | None = None,
        vsd_guid: UUID | None = None,
        batch_id: str | None = None,
        product_item_guid: UUID | None = None,
        entered_by: UUID | None = None,
        veterinary_document_id: UUID | None = None,
    ) -> None:
        """Привязывает одну ВСД к партии. Пустые значения не затирают старые."""
        if (
            veterinary_document_id is not None
            and self._veterinary_document_id is not None
            and self._veterinary_document_id != veterinary_document_id
        ):
            raise LotVeterinaryDocumentConflictError(
                lot_id=self._id,
                existing_document_id=self._veterinary_document_id,
                new_document_id=veterinary_document_id,
            )

        if (
            vsd_guid is not None
            and self._vetis_vsd_guid is not None
            and self._vetis_vsd_guid != vsd_guid
        ):
            raise LotVetisConflictError(
                lot_id=self._id,
                existing_guid=self._vetis_vsd_guid,
                new_guid=vsd_guid,
            )

        has_vetis = any(
            value is not None
            for value in (
                vsd_number,
                vsd_guid,
                batch_id,
                product_item_guid,
                veterinary_document_id,
            )
        )
        if not has_vetis:
            return

        self._veterinary_document_id = (
            veterinary_document_id or self._veterinary_document_id
        )
        self._vetis_vsd_number = vsd_number or self._vetis_vsd_number
        self._vetis_vsd_guid = vsd_guid or self._vetis_vsd_guid
        self._vetis_batch_id = batch_id or self._vetis_batch_id
        self._vetis_product_item_guid = (
            product_item_guid or self._vetis_product_item_guid
        )
        self._vetis_entered_at = get_datetime_utc()
        self._vetis_entered_by = entered_by or self._vetis_entered_by

    def is_expired(self, on: date) -> bool:
        if self._expires_at is None:
            return False
        return self._expires_at < on
