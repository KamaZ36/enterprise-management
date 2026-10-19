"""inventory counts

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-10-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUANTITY = sa.Numeric(18, 6)
SCHEMA = "inventory"


def upgrade() -> None:
    op.create_table(
        "inventory_counts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_counts")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_counts_org_unit_occurred_at",
        "inventory_counts",
        ["org_unit_id", "occurred_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_counts_status",
        "inventory_counts",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "inventory_count_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inventory_count_id", sa.UUID(), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("counted_quantity", QUANTITY, nullable=False),
        sa.CheckConstraint(
            "counted_quantity >= 0",
            name=op.f("counted_quantity_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["inventory_count_id"],
            [f"{SCHEMA}.inventory_counts.id"],
            name=op.f("fk_inventory_count_lines_inventory_count_id_inventory_counts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            [f"{SCHEMA}.stock_lots.id"],
            name=op.f("fk_inventory_count_lines_lot_id_stock_lots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_count_lines")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_count_lines_inventory_count_id",
        "inventory_count_lines",
        ["inventory_count_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_count_lines_inventory_count_id",
        table_name="inventory_count_lines",
        schema=SCHEMA,
    )
    op.drop_table("inventory_count_lines", schema=SCHEMA)
    op.drop_index(
        "ix_inventory_counts_status", table_name="inventory_counts", schema=SCHEMA
    )
    op.drop_index(
        "ix_inventory_counts_org_unit_occurred_at",
        table_name="inventory_counts",
        schema=SCHEMA,
    )
    op.drop_table("inventory_counts", schema=SCHEMA)
