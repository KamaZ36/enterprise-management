"""pos sales import

Revision ID: e8c9d0f1a2b3
Revises: d7b8c9e0f1a2
Create Date: 2026-10-27 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8c9d0f1a2b3"
down_revision: str | Sequence[str] | None = "d7b8c9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "pos"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("doka_org_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint(
            "doka_org_id", name="uq_pos_sources_doka_org_id"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_sources_org_unit_id",
        "sources",
        ["org_unit_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "agents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("install_id", sa.String(length=64), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("api_key_prefix", sa.String(length=16), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="ok", nullable=False),
        sa.Column(
            "pending_receipts", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1024), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
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
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.sources.id"],
            name=op.f("fk_agents_source_id_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agents")),
        sa.UniqueConstraint("api_key_hash", name="uq_pos_agents_api_key_hash"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_agents_source_id",
        "agents",
        ["source_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_pos_agents_source_install",
        "agents",
        ["source_id", "install_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("install_id is not null"),
    )

    op.create_table(
        "import_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "receipts_total", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_created", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_duplicate", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_posted", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_pending", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "receipts_failed", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=16), server_default="received", nullable=False
        ),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.sources.id"],
            name=op.f("fk_import_batches_source_id_sources"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            [f"{SCHEMA}.agents.id"],
            name=op.f("fk_import_batches_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_import_batches_source_received",
        "import_batches",
        ["source_id", "received_at"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("batch_id", sa.UUID(), nullable=True),
        sa.Column("external_guid", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("payment_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "total_kopecks", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("subdivision_code", sa.String(length=32), nullable=True),
        sa.Column("subdivision_name", sa.String(length=255), nullable=True),
        sa.Column("cashier", sa.String(length=255), nullable=True),
        sa.Column("shift", sa.String(length=32), nullable=True),
        sa.Column("number", sa.String(length=32), nullable=True),
        sa.Column("fd_number", sa.String(length=32), nullable=True),
        sa.Column("fp_number", sa.String(length=32), nullable=True),
        sa.Column("fn_number", sa.String(length=32), nullable=True),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default="new", nullable=False
        ),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False
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
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.sources.id"],
            name=op.f("fk_receipts_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            [f"{SCHEMA}.agents.id"],
            name=op.f("fk_receipts_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            [f"{SCHEMA}.import_batches.id"],
            name=op.f("fk_receipts_batch_id_import_batches"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipts")),
        sa.UniqueConstraint(
            "source_id",
            "external_guid",
            name="uq_pos_receipts_source_guid",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipts_status",
        "receipts",
        ["status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipts_source_occurred_at",
        "receipts",
        ["source_id", "occurred_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipts_org_unit_occurred_at",
        "receipts",
        ["org_unit_id", "occurred_at"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "receipt_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("receipt_id", sa.UUID(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("external_guid", sa.String(length=64), nullable=True),
        sa.Column("product_guid", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=512), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column(
            "unit_factor",
            sa.Numeric(precision=18, scale=6),
            server_default="1",
            nullable=False,
        ),
        sa.Column("price_kopecks", sa.BigInteger(), nullable=False),
        sa.Column("amount_kopecks", sa.BigInteger(), nullable=False),
        sa.Column(
            "discount_kopecks", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("mark_code", sa.String(length=128), nullable=True),
        sa.Column("nomenclature_id", sa.UUID(), nullable=True),
        sa.Column(
            "mapping_status",
            sa.String(length=16),
            server_default="unmapped",
            nullable=False,
        ),
        sa.Column("mapping_error", sa.String(length=512), nullable=True),
        sa.Column(
            "raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            [f"{SCHEMA}.receipts.id"],
            name=op.f("fk_receipt_lines_receipt_id_receipts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receipt_lines")),
        sa.UniqueConstraint(
            "receipt_id",
            "line_number",
            name="uq_pos_receipt_lines_receipt_line",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipt_lines_receipt_id",
        "receipt_lines",
        ["receipt_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipt_lines_product_guid",
        "receipt_lines",
        ["product_guid"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_receipt_lines_nomenclature_id",
        "receipt_lines",
        ["nomenclature_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "product_map",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("doka_product_guid", sa.String(length=64), nullable=False),
        sa.Column("nomenclature_id", sa.UUID(), nullable=False),
        sa.Column(
            "unit_factor",
            sa.Numeric(precision=18, scale=6),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
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
        sa.ForeignKeyConstraint(
            ["source_id"],
            [f"{SCHEMA}.sources.id"],
            name=op.f("fk_product_map_source_id_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_map")),
        sa.UniqueConstraint(
            "source_id",
            "doka_product_guid",
            name="uq_pos_product_map_source_product",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_pos_product_map_nomenclature_id",
        "product_map",
        ["nomenclature_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("product_map", schema=SCHEMA)
    op.drop_table("receipt_lines", schema=SCHEMA)
    op.drop_table("receipts", schema=SCHEMA)
    op.drop_table("import_batches", schema=SCHEMA)
    op.drop_table("agents", schema=SCHEMA)
    op.drop_table("sources", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
