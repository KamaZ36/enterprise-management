"""opening balances

Revision ID: c6d7e8f9a0b1
Revises: b5c1d2e3f4a6
Create Date: 2026-11-08 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c6d7e8f9a0b1"
down_revision: str | Sequence[str] | None = "b5c1d2e3f4a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "inventory"

MOVEMENT_TYPES = (
    "receipt",
    "issue",
    "write_off",
    "sale",
    "transfer_out",
    "transfer_in",
    "inventory_surplus",
    "inventory_shortage",
    "production_out",
    "production_in",
    "opening_balance",
)

DOCUMENT_TYPES = (
    "receipt",
    "write_off",
    "transfer",
    "inventory_count",
    "production",
    "sale",
    "opening_balance",
)


def _values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "opening_balances",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_unit_id", UUID(), nullable=False),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("created_by", UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opening_balances")),
        sa.UniqueConstraint("number", name=op.f("uq_opening_balances_number")),
        sa.CheckConstraint(
            f"status IN ({_values(('draft', 'posted', 'cancelled'))})",
            name=op.f("ck_opening_balances_status"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_opening_balances_org_unit_occurred_at",
        "opening_balances",
        ["org_unit_id", "occurred_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_opening_balances_status",
        "opening_balances",
        ["status"],
        schema=SCHEMA,
    )

    op.create_table(
        "opening_balance_lines",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("opening_balance_id", UUID(), nullable=False),
        sa.Column("nomenclature_id", UUID(), nullable=False),
        sa.Column("lot_id", UUID(), nullable=True),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "unit_cost",
            sa.Numeric(18, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_cost",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opening_balance_lines")),
        sa.ForeignKeyConstraint(
            ["opening_balance_id"],
            [f"{SCHEMA}.opening_balances.id"],
            name=op.f(
                "fk_opening_balance_lines_opening_balance_id_opening_balances"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            [f"{SCHEMA}.stock_lots.id"],
            name=op.f("fk_opening_balance_lines_lot_id_stock_lots"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_opening_balance_lines_quantity_positive"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_opening_balance_lines_opening_balance_id",
        "opening_balance_lines",
        ["opening_balance_id"],
        schema=SCHEMA,
    )

    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        sa.text(f"movement_type IN ({_values(MOVEMENT_TYPES)})"),
        schema=SCHEMA,
    )

    op.drop_constraint(
        "document_type",
        "stock_postings",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "document_type",
        "stock_postings",
        sa.text(f"document_type IN ({_values(DOCUMENT_TYPES)})"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "document_type",
        "stock_postings",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "document_type",
        "stock_postings",
        sa.text(f"document_type IN ({_values(DOCUMENT_TYPES[:-1])})"),
        schema=SCHEMA,
    )

    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        sa.text(f"movement_type IN ({_values(MOVEMENT_TYPES[:-1])})"),
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_opening_balance_lines_opening_balance_id",
        table_name="opening_balance_lines",
        schema=SCHEMA,
    )
    op.drop_table("opening_balance_lines", schema=SCHEMA)

    op.drop_index(
        "ix_opening_balances_status",
        table_name="opening_balances",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_opening_balances_org_unit_occurred_at",
        table_name="opening_balances",
        schema=SCHEMA,
    )
    op.drop_table("opening_balances", schema=SCHEMA)
