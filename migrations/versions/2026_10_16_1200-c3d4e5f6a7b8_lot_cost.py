"""lot cost

Revision ID: c3d4e5f6a7b8
Revises: i8f7d4e0a3c5
Create Date: 2026-10-16 12:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "i8f7d4e0a3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "inventory"

BACKFILL = """
WITH lots AS (
    SELECT lb.warehouse_id,
           lb.nomenclature_id,
           lb.lot_id,
           lb.quantity,
           sb.total_value AS nom_value,
           sb.quantity AS nom_quantity
    FROM inventory.stock_lot_balances lb
    JOIN inventory.stock_balances sb
      ON sb.warehouse_id = lb.warehouse_id
     AND sb.nomenclature_id = lb.nomenclature_id
    WHERE sb.quantity > 0
      AND lb.quantity > 0
),
base AS (
    SELECT warehouse_id,
           nomenclature_id,
           lot_id,
           quantity,
           floor(nom_value * quantity / nom_quantity) AS base_value,
           nom_value - sum(floor(nom_value * quantity / nom_quantity))
               OVER (PARTITION BY warehouse_id, nomenclature_id) AS remainder,
           row_number() OVER (
               PARTITION BY warehouse_id, nomenclature_id
               ORDER BY quantity DESC, lot_id
           ) AS rn
    FROM lots
)
UPDATE inventory.stock_lot_balances lb
SET total_value = a.base_value + CASE WHEN a.rn <= a.remainder THEN 1 ELSE 0 END,
    average_unit_cost = round(
        (a.base_value + CASE WHEN a.rn <= a.remainder THEN 1 ELSE 0 END)
        / lb.quantity,
        6
    )
FROM base a
WHERE lb.warehouse_id = a.warehouse_id
  AND lb.nomenclature_id = a.nomenclature_id
  AND lb.lot_id = a.lot_id
"""


def upgrade() -> None:
    op.add_column(
        "stock_lot_balances",
        sa.Column("total_value", sa.BigInteger(), nullable=False, server_default="0"),
        schema=SCHEMA,
    )
    op.add_column(
        "stock_lot_balances",
        sa.Column(
            "average_unit_cost",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="0",
        ),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "total_value_non_negative",
        "stock_lot_balances",
        "total_value >= 0",
        schema=SCHEMA,
    )

    op.execute(BACKFILL)


def downgrade() -> None:
    op.drop_constraint(
        "total_value_non_negative",
        "stock_lot_balances",
        schema=SCHEMA,
        type_="check",
    )
    op.drop_column("stock_lot_balances", "average_unit_cost", schema=SCHEMA)
    op.drop_column("stock_lot_balances", "total_value", schema=SCHEMA)
