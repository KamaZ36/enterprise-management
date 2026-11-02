"""veterinary documents

Revision ID: a1b2c3d4e5f7
Revises: e9f0a1b2c3d4
Create Date: 2026-10-31 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str | Sequence[str] | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "veterinary"
INVENTORY = "inventory"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS veterinary")

    op.create_table(
        "veterinary_documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.String(length=64), nullable=True),
        sa.Column("guid", sa.UUID(), nullable=True),
        sa.Column("batch_id", sa.String(length=255), nullable=True),
        sa.Column("product_item_guid", sa.UUID(), nullable=True),
        sa.Column(
            "source", sa.String(length=16), nullable=False, server_default="manual"
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_veterinary_documents_org_unit_id",
        "veterinary_documents",
        ["org_unit_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_veterinary_documents_guid",
        "veterinary_documents",
        ["guid"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_veterinary_documents_number",
        "veterinary_documents",
        ["number"],
        schema=SCHEMA,
    )

    op.add_column(
        "stock_lots",
        sa.Column("veterinary_document_id", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.create_index(
        "ix_stock_lots_veterinary_document_id",
        "stock_lots",
        ["veterinary_document_id"],
        schema=INVENTORY,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_lots_veterinary_document_id",
        table_name="stock_lots",
        schema=INVENTORY,
    )
    op.drop_column("stock_lots", "veterinary_document_id", schema=INVENTORY)

    op.drop_index(
        "ix_veterinary_documents_number",
        table_name="veterinary_documents",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_veterinary_documents_guid",
        table_name="veterinary_documents",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_veterinary_documents_org_unit_id",
        table_name="veterinary_documents",
        schema=SCHEMA,
    )
    op.drop_table("veterinary_documents", schema=SCHEMA)
