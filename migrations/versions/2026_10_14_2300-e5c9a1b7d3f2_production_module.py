from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e5c9a1b7d3f2"
down_revision: str | Sequence[str] | None = "d2b5e8f0a4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "production"
INVENTORY_SCHEMA = "inventory"
QUANTITY = sa.Numeric(18, 6)


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "tech_cards",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("basis", sa.String(16), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("comment", sa.String(512), nullable=True),
        sa.Column("created_by", UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("code", "version", name="uq_tech_cards_code_version"),
        schema=SCHEMA,
    )
    op.create_index("ix_tech_cards_code", "tech_cards", ["code"], schema=SCHEMA)

    op.create_table(
        "tech_card_lines",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "tech_card_id",
            UUID(),
            sa.ForeignKey(f"{SCHEMA}.tech_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("nomenclature_id", UUID(), nullable=True),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("loss_kind", sa.String(16), nullable=True),
        sa.Column("output_kind", sa.String(16), nullable=True),
        sa.Column("cost_coefficient", QUANTITY, nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tech_card_lines_tech_card_id",
        "tech_card_lines",
        ["tech_card_id"],
        schema=SCHEMA,
    )

    op.create_table(
        "production_orders",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "warehouse_id",
            UUID(),
            sa.ForeignKey(
                f"{INVENTORY_SCHEMA}.warehouses.id", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        sa.Column(
            "tech_card_id",
            UUID(),
            sa.ForeignKey(f"{SCHEMA}.tech_cards.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tech_card_code", sa.String(64), nullable=False),
        sa.Column("tech_card_version", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="draft"
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("batch_count", QUANTITY, nullable=False),
        sa.Column("comment", sa.String(512), nullable=True),
        sa.Column("created_by", UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_production_orders_warehouse_id",
        "production_orders",
        ["warehouse_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_production_orders_status",
        "production_orders",
        ["status"],
        schema=SCHEMA,
    )

    op.create_table(
        "production_order_lines",
        sa.Column("id", UUID(), primary_key=True),
        sa.Column(
            "order_id",
            UUID(),
            sa.ForeignKey(f"{SCHEMA}.production_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("nomenclature_id", UUID(), nullable=True),
        sa.Column("loss_kind", sa.String(16), nullable=True),
        sa.Column("output_kind", sa.String(16), nullable=True),
        sa.Column("cost_coefficient", QUANTITY, nullable=True),
        sa.Column("planned_quantity", QUANTITY, nullable=False),
        sa.Column("actual_quantity", QUANTITY, nullable=False),
        sa.Column("cost", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_production_order_lines_order_id",
        "production_order_lines",
        ["order_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_order_lines_order_id",
        table_name="production_order_lines",
        schema=SCHEMA,
    )
    op.drop_table("production_order_lines", schema=SCHEMA)

    op.drop_index(
        "ix_production_orders_status",
        table_name="production_orders",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_production_orders_warehouse_id",
        table_name="production_orders",
        schema=SCHEMA,
    )
    op.drop_table("production_orders", schema=SCHEMA)

    op.drop_index(
        "ix_tech_card_lines_tech_card_id",
        table_name="tech_card_lines",
        schema=SCHEMA,
    )
    op.drop_table("tech_card_lines", schema=SCHEMA)

    op.drop_index("ix_tech_cards_code", table_name="tech_cards", schema=SCHEMA)
    op.drop_table("tech_cards", schema=SCHEMA)
