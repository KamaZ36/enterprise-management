from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5b2c8f1a3e7"
down_revision: str | Sequence[str] | None = "c4a1b7e2d9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUANTITY = sa.Numeric(18, 6)
SCHEMA = "inventory"


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_warehouse_id", sa.UUID(), nullable=False),
        sa.Column("to_warehouse_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["from_warehouse_id"],
            [f"{SCHEMA}.warehouses.id"],
            name=op.f("fk_transfers_from_warehouse_id_warehouses"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_warehouse_id"],
            [f"{SCHEMA}.warehouses.id"],
            name=op.f("fk_transfers_to_warehouse_id_warehouses"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfers")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transfers_from_occurred_at",
        "transfers",
        ["from_warehouse_id", "occurred_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transfers_to_occurred_at",
        "transfers",
        ["to_warehouse_id", "occurred_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transfers_status", "transfers", ["status"], unique=False, schema=SCHEMA
    )

    op.create_table(
        "transfer_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transfer_id", sa.UUID(), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=False),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("transfer_lines_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["transfer_id"],
            [f"{SCHEMA}.transfers.id"],
            name=op.f("fk_transfer_lines_transfer_id_transfers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            [f"{SCHEMA}.stock_lots.id"],
            name=op.f("fk_transfer_lines_lot_id_stock_lots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfer_lines")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_transfer_lines_transfer_id",
        "transfer_lines",
        ["transfer_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transfer_lines_transfer_id", table_name="transfer_lines", schema=SCHEMA
    )
    op.drop_table("transfer_lines", schema=SCHEMA)
    op.drop_index("ix_transfers_status", table_name="transfers", schema=SCHEMA)
    op.drop_index("ix_transfers_to_occurred_at", table_name="transfers", schema=SCHEMA)
    op.drop_index("ix_transfers_from_occurred_at", table_name="transfers", schema=SCHEMA)
    op.drop_table("transfers", schema=SCHEMA)
