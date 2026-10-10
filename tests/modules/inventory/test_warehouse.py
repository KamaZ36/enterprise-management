from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import EmptyFieldError


def test_create_warehouse() -> None:
    org_unit_id = uuid4()

    warehouse = Warehouse.create(
        org_unit_id=org_unit_id,
        code="RAW-1",
        name="Сырьё",
        type=WarehouseType.RAW,
    )

    assert warehouse.org_unit_id == org_unit_id
    assert warehouse.code == "RAW-1"
    assert warehouse.type is WarehouseType.RAW
    assert warehouse.is_active is True


def test_create_rejects_empty_code_and_name() -> None:
    org_unit_id = uuid4()

    with pytest.raises(EmptyFieldError):
        Warehouse.create(
            org_unit_id=org_unit_id, code="  ", name="Сырьё", type=WarehouseType.RAW
        )

    with pytest.raises(EmptyFieldError):
        Warehouse.create(
            org_unit_id=org_unit_id, code="RAW-1", name=" ", type=WarehouseType.RAW
        )


def test_rename_updates_name_and_timestamp() -> None:
    warehouse = Warehouse.create(
        org_unit_id=uuid4(), code="RAW-1", name="Сырьё", type=WarehouseType.RAW
    )
    before = warehouse.updated_at

    warehouse.rename("Сырьё и специи")

    assert warehouse.name == "Сырьё и специи"
    assert warehouse.updated_at >= before


def test_deactivate() -> None:
    warehouse = Warehouse.create(
        org_unit_id=uuid4(), code="RAW-1", name="Сырьё", type=WarehouseType.RAW
    )

    warehouse.deactivate()

    assert warehouse.is_active is False
