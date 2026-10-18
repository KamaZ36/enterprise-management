from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f2b3c4d5e6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sales"

ORDER_STATUSES = (
    "draft",
    "new",
    "confirmed",
    "preparing",
    "ready",
    "completed",
    "cancelled",
)

FULFILLMENT_TYPES = ("pickup", "delivery")
PAYMENT_METHODS = ("online", "on_pickup", "on_delivery")
PAYMENT_STATUSES = ("pending", "paid")


def _check(column: str, values: tuple[str, ...]) -> sa.TextClause:
    joined = ", ".join(f"'{value}'" for value in values)

    return sa.text(f"{column} IN ({joined})")


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "fulfillment_type",
            sa.String(length=16),
            nullable=False,
            server_default="pickup",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column(
            "payment_method",
            sa.String(length=16),
            nullable=False,
            server_default="on_pickup",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column(
            "payment_status",
            sa.String(length=16),
            nullable=False,
            server_default="pending",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column("payment_provider", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column("payment_provider_id", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    op.drop_constraint("status", "orders", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        "status", "orders", _check("status", ORDER_STATUSES), schema=SCHEMA
    )
    op.create_check_constraint(
        "fulfillment_type",
        "orders",
        _check("fulfillment_type", FULFILLMENT_TYPES),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "payment_method",
        "orders",
        _check("payment_method", PAYMENT_METHODS),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "payment_status",
        "orders",
        _check("payment_status", PAYMENT_STATUSES),
        schema=SCHEMA,
    )

    op.create_index(
        "uq_orders_open_cart",
        "orders",
        ["customer_id", "org_unit_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("status = 'draft'"),
    )


def downgrade() -> None:
    op.drop_index("uq_orders_open_cart", table_name="orders", schema=SCHEMA)

    op.drop_constraint("payment_status", "orders", schema=SCHEMA, type_="check")
    op.drop_constraint("payment_method", "orders", schema=SCHEMA, type_="check")
    op.drop_constraint("fulfillment_type", "orders", schema=SCHEMA, type_="check")
    op.drop_constraint("status", "orders", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        "status",
        "orders",
        _check(
            "status",
            ("draft", "confirmed", "preparing", "ready", "completed", "cancelled"),
        ),
        schema=SCHEMA,
    )

    op.drop_column("orders", "paid_at", schema=SCHEMA)
    op.drop_column("orders", "payment_provider_id", schema=SCHEMA)
    op.drop_column("orders", "payment_provider", schema=SCHEMA)
    op.drop_column("orders", "payment_status", schema=SCHEMA)
    op.drop_column("orders", "payment_method", schema=SCHEMA)
    op.drop_column("orders", "fulfillment_type", schema=SCHEMA)
