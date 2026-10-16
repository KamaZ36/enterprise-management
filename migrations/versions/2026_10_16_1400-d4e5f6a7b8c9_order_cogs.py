"""order cogs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-16 14:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SALES = "sales"
INVENTORY = "inventory"

DOCUMENT_TYPES = (
    "receipt",
    "write_off",
    "transfer",
    "inventory_count",
    "production",
    "sale",
)


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("warehouse_id", UUID(), nullable=True),
        schema=SALES,
    )
    op.add_column(
        "order_lines",
        sa.Column("cost_kopecks", sa.BigInteger(), nullable=True),
        schema=SALES,
    )

    joined = ", ".join(f"'{value}'" for value in DOCUMENT_TYPES)
    op.execute(
        f"ALTER TABLE {INVENTORY}.stock_postings "
        "DROP CONSTRAINT ck_stock_postings_document_type"
    )
    op.execute(
        f"ALTER TABLE {INVENTORY}.stock_postings "
        f"ADD CONSTRAINT ck_stock_postings_document_type "
        f"CHECK (document_type IN ({joined}))"
    )


def downgrade() -> None:
    joined = ", ".join(
        f"'{value}'" for value in DOCUMENT_TYPES if value != "sale"
    )
    op.execute(
        f"ALTER TABLE {INVENTORY}.stock_postings "
        "DROP CONSTRAINT ck_stock_postings_document_type"
    )
    op.execute(
        f"ALTER TABLE {INVENTORY}.stock_postings "
        f"ADD CONSTRAINT ck_stock_postings_document_type "
        f"CHECK (document_type IN ({joined}))"
    )

    op.drop_column("order_lines", "cost_kopecks", schema=SALES)
    op.drop_column("orders", "warehouse_id", schema=SALES)
