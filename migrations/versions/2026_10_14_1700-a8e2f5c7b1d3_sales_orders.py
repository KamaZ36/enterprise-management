from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8e2f5c7b1d3"
down_revision: str | Sequence[str] | None = "f7d4e1b3c9a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sales"


def upgrade() -> None:
    op.execute(f"create schema if not exists {SCHEMA}")

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("day", sa.Date(), nullable=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("org_unit_id", "day", "number", name="uq_orders_number"),
        schema=SCHEMA,
    )
    op.create_index("ix_orders_org_unit_id", "orders", ["org_unit_id"], schema=SCHEMA)
    op.create_index("ix_orders_status", "orders", ["status"], schema=SCHEMA)
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"], schema=SCHEMA)

    op.create_table(
        "order_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            [f"{SCHEMA}.orders.id"],
            name=op.f("fk_order_lines_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_lines")),
        schema=SCHEMA,
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"], schema=SCHEMA)

    op.create_table(
        "order_number_counters",
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "org_unit_id", "day", name=op.f("pk_order_number_counters")
        ),
        schema=SCHEMA,
    )

    # Замки на перечисления: база не примет значение, которого не знает код.
    op.create_check_constraint(
        "channel",
        "orders",
        sa.text("channel IN ('site', 'pos', 'phone')"),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "status",
        "orders",
        sa.text(
            "status IN ('draft', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled')"
        ),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "quantity", "order_lines", sa.text("quantity > 0"), schema=SCHEMA
    )
    op.create_check_constraint(
        "unit_price", "order_lines", sa.text("unit_price >= 0"), schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("order_number_counters", schema=SCHEMA)
    op.drop_table("order_lines", schema=SCHEMA)
    op.drop_table("orders", schema=SCHEMA)
