"""ofd receipts

Revision ID: c5e6f7a8b9d0
Revises: aa9e8d8ad1db
Create Date: 2026-10-24 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5e6f7a8b9d0"
down_revision: str | Sequence[str] | None = "aa9e8d8ad1db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "fiscal"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "ofd_sync_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("reg_number", sa.String(length=16), nullable=False),
        sa.Column("period_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default="running", nullable=False
        ),
        sa.Column(
            "receipts_found", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_created", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ofd_sync_runs")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_sync_runs_reg_number_started_at",
        "ofd_sync_runs",
        ["reg_number", "started_at"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "ofd_receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column("reg_number", sa.String(length=16), nullable=False),
        sa.Column("fn_number", sa.String(length=32), nullable=False),
        sa.Column("doc_number", sa.BigInteger(), nullable=False),
        sa.Column("fiscal_sign", sa.String(length=32), nullable=False),
        sa.Column("raw_id", sa.String(length=64), nullable=True),
        sa.Column("doc_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("c_date_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column(
            "is_correction", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "is_bso", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "total_kopecks", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column(
            "cash_kopecks", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column(
            "ecash_kopecks", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("org_unit_id", sa.UUID(), nullable=True),
        sa.Column(
            "status", sa.String(length=24), server_default="new", nullable=False
        ),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", sa.UUID(), nullable=True),
        sa.Column(
            "raw",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ofd_receipts")),
        sa.UniqueConstraint(
            "reg_number",
            "fn_number",
            "doc_number",
            "fiscal_sign",
            name="uq_ofd_receipts_identity",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipts_status",
        "ofd_receipts",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipts_reg_number_doc_datetime",
        "ofd_receipts",
        ["reg_number", "doc_datetime"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipts_org_unit_doc_datetime",
        "ofd_receipts",
        ["org_unit_id", "doc_datetime"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "ofd_receipt_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column(
            "product_code",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("price_kopecks", sa.BigInteger(), nullable=False),
        sa.Column("total_kopecks", sa.BigInteger(), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=True),
        sa.Column(
            "mapping_status",
            sa.String(length=16),
            server_default="unmapped",
            nullable=False,
        ),
        sa.Column("mapping_error", sa.String(length=512), nullable=True),
        sa.Column(
            "raw",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["fiscal.ofd_receipts.id"],
            name=op.f("fk_ofd_receipt_lines_receipt_id_ofd_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ofd_receipt_lines")),
        sa.UniqueConstraint(
            "receipt_id",
            "line_number",
            name="uq_ofd_receipt_lines_receipt_line",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipt_lines_receipt_id",
        "ofd_receipt_lines",
        ["receipt_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipt_lines_barcode",
        "ofd_receipt_lines",
        ["barcode"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_receipt_lines_nomenclature_id",
        "ofd_receipt_lines",
        ["nomenclature_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "ofd_product_aliases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ofd_product_aliases")),
        sa.UniqueConstraint(
            "barcode", name="uq_ofd_product_aliases_barcode"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ofd_product_aliases_nomenclature_id",
        "ofd_product_aliases",
        ["nomenclature_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("ofd_product_aliases", schema=SCHEMA)
    op.drop_table("ofd_receipt_lines", schema=SCHEMA)
    op.drop_table("ofd_receipts", schema=SCHEMA)
    op.drop_table("ofd_sync_runs", schema=SCHEMA)
