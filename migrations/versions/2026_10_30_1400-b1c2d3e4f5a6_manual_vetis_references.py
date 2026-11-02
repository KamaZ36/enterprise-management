"""manual vetis references

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-10-30 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INVENTORY = "inventory"
PRODUCTION = "production"


def upgrade() -> None:
    op.add_column(
        "receipt_lines",
        sa.Column("vetis_vsd_number", sa.String(length=64), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "receipt_lines",
        sa.Column("vetis_vsd_guid", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "receipt_lines",
        sa.Column("vetis_product_item_guid", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "receipt_lines",
        sa.Column("vetis_batch_id", sa.String(length=255), nullable=True),
        schema=INVENTORY,
    )

    op.add_column(
        "stock_lots",
        sa.Column("vetis_vsd_number", sa.String(length=64), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "stock_lots",
        sa.Column("vetis_vsd_guid", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "stock_lots",
        sa.Column("vetis_batch_id", sa.String(length=255), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "stock_lots",
        sa.Column("vetis_product_item_guid", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "stock_lots",
        sa.Column("vetis_entered_at", sa.DateTime(timezone=True), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "stock_lots",
        sa.Column("vetis_entered_by", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.create_index(
        "ix_stock_lots_vetis_vsd_guid",
        "stock_lots",
        ["vetis_vsd_guid"],
        unique=False,
        schema=INVENTORY,
    )

    op.add_column(
        "production_orders",
        sa.Column(
            "vetis_status",
            sa.String(length=16),
            nullable=False,
            server_default="not_specified",
        ),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_orders",
        sa.Column("vetis_operation_id", sa.String(length=64), nullable=True),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_orders",
        sa.Column("vetis_no_vsd_reason", sa.String(length=255), nullable=True),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_orders",
        sa.Column("vetis_entered_by", sa.UUID(), nullable=True),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_orders",
        sa.Column(
            "vetis_entered_at", sa.DateTime(timezone=True), nullable=True
        ),
        schema=PRODUCTION,
    )

    op.add_column(
        "production_order_lines",
        sa.Column(
            "vetis_production_vsd_number", sa.String(length=64), nullable=True
        ),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_order_lines",
        sa.Column("vetis_production_vsd_guid", sa.UUID(), nullable=True),
        schema=PRODUCTION,
    )
    op.add_column(
        "production_order_lines",
        sa.Column("vetis_batch_id", sa.String(length=255), nullable=True),
        schema=PRODUCTION,
    )


def downgrade() -> None:
    op.drop_column(
        "production_order_lines", "vetis_batch_id", schema=PRODUCTION
    )
    op.drop_column(
        "production_order_lines",
        "vetis_production_vsd_guid",
        schema=PRODUCTION,
    )
    op.drop_column(
        "production_order_lines",
        "vetis_production_vsd_number",
        schema=PRODUCTION,
    )

    op.drop_column("production_orders", "vetis_entered_at", schema=PRODUCTION)
    op.drop_column("production_orders", "vetis_entered_by", schema=PRODUCTION)
    op.drop_column(
        "production_orders", "vetis_no_vsd_reason", schema=PRODUCTION
    )
    op.drop_column("production_orders", "vetis_operation_id", schema=PRODUCTION)
    op.drop_column("production_orders", "vetis_status", schema=PRODUCTION)

    op.drop_index(
        "ix_stock_lots_vetis_vsd_guid",
        table_name="stock_lots",
        schema=INVENTORY,
    )
    op.drop_column("stock_lots", "vetis_entered_by", schema=INVENTORY)
    op.drop_column("stock_lots", "vetis_entered_at", schema=INVENTORY)
    op.drop_column("stock_lots", "vetis_product_item_guid", schema=INVENTORY)
    op.drop_column("stock_lots", "vetis_batch_id", schema=INVENTORY)
    op.drop_column("stock_lots", "vetis_vsd_guid", schema=INVENTORY)
    op.drop_column("stock_lots", "vetis_vsd_number", schema=INVENTORY)

    op.drop_column("receipt_lines", "vetis_batch_id", schema=INVENTORY)
    op.drop_column(
        "receipt_lines", "vetis_product_item_guid", schema=INVENTORY
    )
    op.drop_column("receipt_lines", "vetis_vsd_guid", schema=INVENTORY)
    op.drop_column("receipt_lines", "vetis_vsd_number", schema=INVENTORY)
