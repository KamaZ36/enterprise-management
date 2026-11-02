"""edo incoming documents

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-10-31 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "edo"
INVENTORY = "inventory"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS edo")

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("number", sa.String(length=64), nullable=False),
        sa.Column("doc_date", sa.Date(), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=True),
        sa.Column("supplier_inn", sa.String(length=12), nullable=True),
        sa.Column("delivery_address", sa.String(length=512), nullable=True),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="manual"
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
        "ix_edo_documents_org_unit_id",
        "documents",
        ["org_unit_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_edo_documents_number",
        "documents",
        ["number"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_edo_documents_external_id",
        "documents",
        ["external_id"],
        schema=SCHEMA,
    )

    op.add_column(
        "receipts",
        sa.Column("edo_document_id", sa.UUID(), nullable=True),
        schema=INVENTORY,
    )
    op.add_column(
        "receipts",
        sa.Column("edo_document_number", sa.String(length=64), nullable=True),
        schema=INVENTORY,
    )
    op.create_index(
        "ix_receipts_edo_document_id",
        "receipts",
        ["edo_document_id"],
        schema=INVENTORY,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_receipts_edo_document_id",
        table_name="receipts",
        schema=INVENTORY,
    )
    op.drop_column("receipts", "edo_document_number", schema=INVENTORY)
    op.drop_column("receipts", "edo_document_id", schema=INVENTORY)

    op.drop_index(
        "ix_edo_documents_external_id",
        table_name="documents",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_edo_documents_number",
        table_name="documents",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_edo_documents_org_unit_id",
        table_name="documents",
        schema=SCHEMA,
    )
    op.drop_table("documents", schema=SCHEMA)
