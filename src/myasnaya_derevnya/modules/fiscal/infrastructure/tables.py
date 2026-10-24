from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    CheckConstraint,
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

DATABASE_SCHEMA = "fiscal"

CASH_REGISTERS_TABLE = Table(
    "cash_registers",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("reg_number", String(16), nullable=True),
    Column("serial_number", String(32), nullable=True),
    Column("name", String(255), nullable=False),
    Column("fiscal_place", String(255), nullable=True),
    Column("model", String(128), nullable=True),
    Column("fn_number", String(32), nullable=True),
    Column("ffd_version", String(8), nullable=True),
    Column("company_id", UUID, nullable=True),
    Column("registered_at", DateTime(timezone=True), nullable=True),
    Column("deregistered_at", DateTime(timezone=True), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("attributes", JSONB, nullable=False, server_default="{}"),
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
    UniqueConstraint("reg_number", name="uq_cash_registers_reg_number"),
    Index("ix_cash_registers_serial_number", "serial_number"),
    schema=DATABASE_SCHEMA,
)

CASH_REGISTER_BINDINGS_TABLE = Table(
    "cash_register_bindings",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "cash_register_id",
        UUID,
        ForeignKey("fiscal.cash_registers.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("org_unit_id", UUID, nullable=False),
    Column("effective_from", DateTime(timezone=True), nullable=False),
    Column("effective_to", DateTime(timezone=True), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint(
        "effective_to is null or effective_to > effective_from", name="period"
    ),
    Index("ix_cash_register_bindings_cash_register_id", "cash_register_id"),
    Index("ix_cash_register_bindings_org_unit_id", "org_unit_id"),
    Index(
        "uq_cash_register_bindings_open",
        "cash_register_id",
        unique=True,
        postgresql_where=text("effective_to is null"),
    ),
    schema=DATABASE_SCHEMA,
)

OFD_SYNC_RUNS_TABLE = Table(
    "ofd_sync_runs",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("inn", String(12), nullable=False),
    Column("reg_number", String(16), nullable=False),
    Column("period_from", DateTime(timezone=True), nullable=False),
    Column("period_to", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", String(16), nullable=False, server_default="running"),
    Column("receipts_found", Integer, nullable=False, server_default="0"),
    Column("receipts_created", Integer, nullable=False, server_default="0"),
    Column("error", String(1024), nullable=True),
    Index("ix_ofd_sync_runs_reg_number_started_at", "reg_number", "started_at"),
    schema=DATABASE_SCHEMA,
)

OFD_RECEIPTS_TABLE = Table(
    "ofd_receipts",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("inn", String(12), nullable=False),
    Column("reg_number", String(16), nullable=False),
    Column("fn_number", String(32), nullable=False),
    Column("doc_number", BigInteger, nullable=False),
    Column("fiscal_sign", String(32), nullable=False),
    Column("raw_id", String(64), nullable=True),
    Column("doc_datetime", DateTime(timezone=True), nullable=False),
    Column("c_date_utc", DateTime(timezone=True), nullable=True),
    Column("operation_type", String(32), nullable=False),
    Column("is_correction", Boolean, nullable=False, server_default="false"),
    Column("is_bso", Boolean, nullable=False, server_default="false"),
    Column("total_kopecks", BigInteger, nullable=False, server_default="0"),
    Column("cash_kopecks", BigInteger, nullable=False, server_default="0"),
    Column("ecash_kopecks", BigInteger, nullable=False, server_default="0"),
    Column("org_unit_id", UUID, nullable=True),
    Column("status", String(24), nullable=False, server_default="new"),
    Column("error", String(1024), nullable=True),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Column("posted_by", UUID, nullable=True),
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
        "reg_number",
        "fn_number",
        "doc_number",
        "fiscal_sign",
        name="uq_ofd_receipts_identity",
    ),
    Index("ix_ofd_receipts_status", "status"),
    Index("ix_ofd_receipts_reg_number_doc_datetime", "reg_number", "doc_datetime"),
    Index("ix_ofd_receipts_org_unit_doc_datetime", "org_unit_id", "doc_datetime"),
    schema=DATABASE_SCHEMA,
)

OFD_RECEIPT_LINES_TABLE = Table(
    "ofd_receipt_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "receipt_id",
        UUID,
        ForeignKey("fiscal.ofd_receipts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("line_number", Integer, nullable=False),
    Column("name", String(512), nullable=False),
    Column("barcode", String(64), nullable=True),
    Column("product_code", JSONB, nullable=False, server_default="{}"),
    Column("quantity", Numeric(18, 6), nullable=False),
    Column("unit", String(32), nullable=True),
    Column("price_kopecks", BigInteger, nullable=False),
    Column("total_kopecks", BigInteger, nullable=False),
    Column("nomenclature_id", UUID, nullable=True),
    Column("mapping_status", String(16), nullable=False, server_default="unmapped"),
    Column("mapping_error", String(512), nullable=True),
    Column("raw", JSONB, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint(
        "receipt_id", "line_number", name="uq_ofd_receipt_lines_receipt_line"
    ),
    Index("ix_ofd_receipt_lines_receipt_id", "receipt_id"),
    Index("ix_ofd_receipt_lines_barcode", "barcode"),
    Index("ix_ofd_receipt_lines_nomenclature_id", "nomenclature_id"),
    schema=DATABASE_SCHEMA,
)

OFD_PRODUCT_ALIASES_TABLE = Table(
    "ofd_product_aliases",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("barcode", String(64), nullable=False),
    Column("nomenclature_id", UUID, nullable=False),
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
    UniqueConstraint("barcode", name="uq_ofd_product_aliases_barcode"),
    Index("ix_ofd_product_aliases_nomenclature_id", "nomenclature_id"),
    schema=DATABASE_SCHEMA,
)
