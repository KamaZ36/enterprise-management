"""stock location = org unit; drop warehouses and nomenclature type

Revision ID: e1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-10-17 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INVENTORY = "inventory"
PRODUCTION = "production"
SALES = "sales"
CATALOG = "catalog"

# (table, schema, old_column, new_column)
RENAMED_COLUMNS: tuple[tuple[str, str, str, str], ...] = (
    ("receipts", INVENTORY, "warehouse_id", "org_unit_id"),
    ("write_offs", INVENTORY, "warehouse_id", "org_unit_id"),
    ("stock_postings", INVENTORY, "warehouse_id", "org_unit_id"),
    ("stock_movements", INVENTORY, "warehouse_id", "org_unit_id"),
    ("stock_balances", INVENTORY, "warehouse_id", "org_unit_id"),
    ("stock_lot_balances", INVENTORY, "warehouse_id", "org_unit_id"),
    ("transfers", INVENTORY, "from_warehouse_id", "from_org_unit_id"),
    ("transfers", INVENTORY, "to_warehouse_id", "to_org_unit_id"),
    ("production_orders", PRODUCTION, "warehouse_id", "org_unit_id"),
)

# (schema, old_index_name, new_index_name)
INDEX_RENAMES: tuple[tuple[str, str, str], ...] = (
    (
        INVENTORY,
        "ix_receipts_warehouse_occurred_at",
        "ix_receipts_org_unit_occurred_at",
    ),
    (
        INVENTORY,
        "ix_write_offs_warehouse_occurred_at",
        "ix_write_offs_org_unit_occurred_at",
    ),
    (
        INVENTORY,
        "ix_stock_postings_warehouse_posted_at",
        "ix_stock_postings_org_unit_posted_at",
    ),
    (
        INVENTORY,
        "ix_stock_movements_warehouse_nomenclature",
        "ix_stock_movements_org_unit_nomenclature",
    ),
    (
        PRODUCTION,
        "ix_production_orders_warehouse_id",
        "ix_production_orders_org_unit_id",
    ),
)

# (table, schema, constraint_name, column)
DROPPED_FOREIGN_KEYS: tuple[tuple[str, str, str, str], ...] = (
    ("receipts", INVENTORY, "fk_receipts_warehouse_id_warehouses", "warehouse_id"),
    ("write_offs", INVENTORY, "fk_write_offs_warehouse_id_warehouses", "warehouse_id"),
    (
        "stock_postings",
        INVENTORY,
        "fk_stock_postings_warehouse_id_warehouses",
        "warehouse_id",
    ),
    (
        "stock_movements",
        INVENTORY,
        "fk_stock_movements_warehouse_id_warehouses",
        "warehouse_id",
    ),
    (
        "stock_balances",
        INVENTORY,
        "fk_stock_balances_warehouse_id_warehouses",
        "warehouse_id",
    ),
    (
        "stock_lot_balances",
        INVENTORY,
        "fk_stock_lot_balances_warehouse_id_warehouses",
        "warehouse_id",
    ),
    (
        "transfers",
        INVENTORY,
        "fk_transfers_from_warehouse_id_warehouses",
        "from_warehouse_id",
    ),
    (
        "transfers",
        INVENTORY,
        "fk_transfers_to_warehouse_id_warehouses",
        "to_warehouse_id",
    ),
    (
        "production_orders",
        PRODUCTION,
        "fk_production_orders_warehouse_id_warehouses",
        "warehouse_id",
    ),
)


def upgrade() -> None:
    for table, schema, constraint_name, _column in DROPPED_FOREIGN_KEYS:
        op.execute(f'ALTER TABLE {schema}."{table}" DROP CONSTRAINT "{constraint_name}"')

    for schema, old_name, new_name in INDEX_RENAMES:
        op.execute(f'ALTER INDEX {schema}."{old_name}" RENAME TO "{new_name}"')

    for table, schema, old_column, new_column in RENAMED_COLUMNS:
        op.alter_column(table, old_column, new_column_name=new_column, schema=schema)

    # Склады больше не существуют: складская локация — это подразделение.
    op.drop_table("warehouses", schema=INVENTORY)

    # Заказ продажи списывается со своего подразделения, отдельный склад не нужен.
    op.drop_column("orders", "warehouse_id", schema=SALES)

    # Тип номенклатуры не функционален — убираем.
    op.execute('ALTER TABLE catalog."nomenclatures" DROP CONSTRAINT "ck_nomenclatures_type"')
    op.drop_index("ix_nomenclatures_type", table_name="nomenclatures", schema=CATALOG)
    op.drop_column("nomenclatures", "type", schema=CATALOG)


def downgrade() -> None:
    op.add_column(
        "nomenclatures",
        sa.Column(
            "type",
            sa.String(length=32),
            nullable=False,
            server_default="raw_material",
        ),
        schema=CATALOG,
    )
    op.alter_column("nomenclatures", "type", server_default=None, schema=CATALOG)
    op.create_index(
        "ix_nomenclatures_type",
        "nomenclatures",
        ["type"],
        unique=False,
        schema=CATALOG,
    )
    op.execute(
        'ALTER TABLE catalog."nomenclatures" ADD CONSTRAINT "ck_nomenclatures_type" '
        "CHECK (type IN ('raw_material', 'semi_finished', 'finished_good'))"
    )

    op.add_column(
        "orders", sa.Column("warehouse_id", sa.UUID(), nullable=True), schema=SALES
    )

    op.create_table(
        "warehouses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_warehouses"),
        sa.UniqueConstraint("code", name="uq_warehouses_code"),
        schema=INVENTORY,
    )
    op.create_index(
        "ix_warehouses_org_unit_id",
        "warehouses",
        ["org_unit_id"],
        unique=False,
        schema=INVENTORY,
    )
    op.execute(
        'ALTER TABLE inventory."warehouses" ADD CONSTRAINT "ck_warehouses_type" '
        "CHECK (type IN ('raw', 'production', 'finished', 'shop'))"
    )

    for table, schema, old_column, new_column in RENAMED_COLUMNS:
        op.alter_column(table, new_column, new_column_name=old_column, schema=schema)

    for schema, old_name, new_name in INDEX_RENAMES:
        op.execute(f'ALTER INDEX {schema}."{new_name}" RENAME TO "{old_name}"')

    for table, schema, constraint_name, column in DROPPED_FOREIGN_KEYS:
        op.execute(
            f'ALTER TABLE {schema}."{table}" ADD CONSTRAINT "{constraint_name}" '
            f'FOREIGN KEY ("{column}") '
            f'REFERENCES inventory."warehouses" ("id") ON DELETE RESTRICT'
        )
