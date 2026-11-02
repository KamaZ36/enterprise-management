"""stock lot identity

Revision ID: a9b8c7d6e5f4
Revises: f3a4b5c6d7e8
Create Date: 2026-10-30 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: str | Sequence[str] | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "inventory"


def upgrade() -> None:
    op.add_column(
        "stock_lots",
        sa.Column("origin_org_unit_id", sa.UUID(), nullable=True),
        schema=SCHEMA,
    )

    op.execute(
        """
        UPDATE inventory.stock_lots AS lot
        SET origin_org_unit_id = balance.org_unit_id
        FROM (
            SELECT DISTINCT ON (lot_id) lot_id, org_unit_id
            FROM inventory.stock_lot_balances
            ORDER BY lot_id, org_unit_id
        ) AS balance
        WHERE balance.lot_id = lot.id
          AND lot.origin_org_unit_id IS NULL
        """
    )

    op.drop_constraint(
        "uq_stock_lots_nomenclature_lot_code",
        "stock_lots",
        schema=SCHEMA,
        type_="unique",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_stock_lots_identity
        ON inventory.stock_lots (
            nomenclature_id,
            lot_code,
            produced_at,
            supplier_name
        )
        NULLS NOT DISTINCT
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX inventory.uq_stock_lots_identity")
    op.create_unique_constraint(
        "uq_stock_lots_nomenclature_lot_code",
        "stock_lots",
        ["nomenclature_id", "lot_code"],
        schema=SCHEMA,
    )
    op.drop_column("stock_lots", "origin_org_unit_id", schema=SCHEMA)
