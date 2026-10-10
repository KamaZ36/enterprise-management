from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    NomenclatureNotAllowedInWarehouseError,
)
from myasnaya_derevnya.modules.inventory.domain.services.warehouse_purpose import (
    WarehousePurposePolicy,
)

POLICY = WarehousePurposePolicy()


def make_warehouse(type: WarehouseType) -> Warehouse:
    return Warehouse.create(org_unit_id=uuid4(), code="W-1", name="Склад", type=type)


def test_raw_warehouse_accepts_only_raw_materials() -> None:
    assert POLICY.allows(WarehouseType.RAW, "raw_material") is True
    assert POLICY.allows(WarehouseType.RAW, "semi_finished") is False
    assert POLICY.allows(WarehouseType.RAW, "finished_good") is False


def test_finished_warehouse_accepts_semi_and_finished() -> None:
    assert POLICY.allows(WarehouseType.FINISHED, "finished_good") is True
    assert POLICY.allows(WarehouseType.FINISHED, "semi_finished") is True
    assert POLICY.allows(WarehouseType.FINISHED, "raw_material") is False


def test_shop_accepts_only_finished_goods() -> None:
    assert POLICY.allows(WarehouseType.SHOP, "finished_good") is True
    assert POLICY.allows(WarehouseType.SHOP, "raw_material") is False


def test_ensure_allowed_raises_with_context() -> None:
    warehouse = make_warehouse(WarehouseType.RAW)
    nomenclature_id = uuid4()

    with pytest.raises(NomenclatureNotAllowedInWarehouseError) as error:
        POLICY.ensure_allowed(
            warehouse=warehouse,
            nomenclature_id=nomenclature_id,
            nomenclature_type_code="finished_good",
        )

    assert error.value.warehouse_id == warehouse.id
    assert error.value.nomenclature_id == nomenclature_id
    assert error.value.warehouse_type == "raw"
    assert error.value.nomenclature_type == "finished_good"


def test_ensure_allowed_passes_for_compatible_type() -> None:
    warehouse = make_warehouse(WarehouseType.RAW)

    POLICY.ensure_allowed(
        warehouse=warehouse,
        nomenclature_id=uuid4(),
        nomenclature_type_code="raw_material",
    )
