from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "pos"

QUANTITY = Numeric(18, 6)
COEFFICIENT = Numeric(18, 6)


POS_SOURCES_TABLE = Table(
    "sources",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("doka_org_id", String(32), nullable=False),
    Column("name", String(255), nullable=False),
    Column("org_unit_id", UUID, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    UniqueConstraint("doka_org_id", name="uq_pos_sources_doka_org_id"),
    Index("ix_pos_sources_org_unit_id", "org_unit_id"),
    schema=DATABASE_SCHEMA,
)


POS_AGENTS_TABLE = Table(
    "agents",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "source_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.sources.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("install_id", String(64), nullable=True),
    Column("api_key_hash", String(64), nullable=False),
    Column("api_key_prefix", String(16), nullable=False),
    Column("hostname", String(255), nullable=True),
    Column("version", String(32), nullable=True),
    Column("status", String(16), nullable=False, server_default="ok"),
    Column("pending_receipts", Integer, nullable=False, server_default="0"),
    Column("last_seen_at", DateTime(timezone=True), nullable=True),
    Column("last_success_at", DateTime(timezone=True), nullable=True),
    Column("last_error", String(1024), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    UniqueConstraint("api_key_hash", name="uq_pos_agents_api_key_hash"),
    Index("ix_pos_agents_source_id", "source_id"),
    Index(
        "uq_pos_agents_source_install",
        "source_id",
        "install_id",
        unique=True,
        postgresql_where=text("install_id is not null"),
    ),
    schema=DATABASE_SCHEMA,
)


POS_IMPORT_BATCHES_TABLE = Table(
    "import_batches",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "source_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.sources.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "agent_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.agents.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("file_name", String(512), nullable=False),
    Column("file_sha256", String(64), nullable=True),
    Column("exported_at", DateTime(timezone=True), nullable=True),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("receipts_total", Integer, nullable=False, server_default="0"),
    Column("receipts_created", Integer, nullable=False, server_default="0"),
    Column("receipts_duplicate", Integer, nullable=False, server_default="0"),
    Column("receipts_posted", Integer, nullable=False, server_default="0"),
    Column("receipts_pending", Integer, nullable=False, server_default="0"),
    Column("receipts_failed", Integer, nullable=False, server_default="0"),
    Column("status", String(16), nullable=False, server_default="received"),
    Column("error", String(1024), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_pos_import_batches_source_received", "source_id", "received_at"),
    schema=DATABASE_SCHEMA,
)


POS_RECEIPTS_TABLE = Table(
    "receipts",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "source_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.sources.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "agent_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.agents.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column(
        "batch_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.import_batches.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("external_guid", String(64), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("payment_kind", String(32), nullable=False),
    Column("total_kopecks", BigInteger, nullable=False, server_default="0"),
    Column("subdivision_code", String(32), nullable=True),
    Column("subdivision_name", String(255), nullable=True),
    Column("cashier", String(255), nullable=True),
    Column("shift", String(32), nullable=True),
    Column("number", String(32), nullable=True),
    Column("fd_number", String(32), nullable=True),
    Column("fp_number", String(32), nullable=True),
    Column("fn_number", String(32), nullable=True),
    Column("org_unit_id", UUID, nullable=False),
    Column("status", String(24), nullable=False, server_default="new"),
    Column("error", String(1024), nullable=True),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Column("raw", JSONB, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    UniqueConstraint(
        "source_id", "external_guid", name="uq_pos_receipts_source_guid"
    ),
    Index("ix_pos_receipts_status", "status"),
    Index(
        "ix_pos_receipts_source_occurred_at", "source_id", "occurred_at"
    ),
    Index(
        "ix_pos_receipts_org_unit_occurred_at", "org_unit_id", "occurred_at"
    ),
    schema=DATABASE_SCHEMA,
)


POS_RECEIPT_LINES_TABLE = Table(
    "receipt_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "receipt_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.receipts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("line_number", Integer, nullable=False),
    Column("external_guid", String(64), nullable=True),
    Column("product_guid", String(64), nullable=False),
    Column("product_name", String(512), nullable=True),
    Column("unit", String(32), nullable=True),
    Column("quantity", QUANTITY, nullable=False),
    Column("unit_factor", COEFFICIENT, nullable=False, server_default="1"),
    Column("price_kopecks", BigInteger, nullable=False),
    Column("amount_kopecks", BigInteger, nullable=False),
    Column("discount_kopecks", BigInteger, nullable=False, server_default="0"),
    Column("barcode", String(64), nullable=True),
    Column("mark_code", String(128), nullable=True),
    Column("nomenclature_id", UUID, nullable=True),
    Column("mapping_status", String(16), nullable=False, server_default="unmapped"),
    Column("mapping_error", String(512), nullable=True),
    Column("raw", JSONB, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint(
        "receipt_id", "line_number", name="uq_pos_receipt_lines_receipt_line"
    ),
    Index("ix_pos_receipt_lines_receipt_id", "receipt_id"),
    Index("ix_pos_receipt_lines_product_guid", "product_guid"),
    Index("ix_pos_receipt_lines_nomenclature_id", "nomenclature_id"),
    schema=DATABASE_SCHEMA,
)


POS_PRODUCT_MAP_TABLE = Table(
    "product_map",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "source_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.sources.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("doka_product_guid", String(64), nullable=False),
    Column("nomenclature_id", UUID, nullable=False),
    Column("unit_factor", COEFFICIENT, nullable=False, server_default="1"),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    UniqueConstraint(
        "source_id", "doka_product_guid", name="uq_pos_product_map_source_product"
    ),
    Index("ix_pos_product_map_nomenclature_id", "nomenclature_id"),
    schema=DATABASE_SCHEMA,
)
