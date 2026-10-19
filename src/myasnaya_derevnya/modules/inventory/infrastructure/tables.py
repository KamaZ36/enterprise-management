from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "inventory"

QUANTITY = Numeric(18, 6)


STOCK_LOTS_TABLE = Table(
    "stock_lots",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("nomenclature_id", UUID, nullable=False),
    Column("lot_code", String(64), nullable=False),
    Column("produced_at", Date, nullable=True),
    Column("expires_at", Date, nullable=True),
    Column("supplier_name", String(255), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint(
        "nomenclature_id", "lot_code", name="uq_stock_lots_nomenclature_lot_code"
    ),
    Index("ix_stock_lots_expires_at", "expires_at"),
    schema=DATABASE_SCHEMA,
)


STOCK_POSTINGS_TABLE = Table(
    "stock_postings",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("document_type", String(32), nullable=False),
    Column("document_id", UUID, nullable=False),
    Column("org_unit_id", UUID, nullable=False),
    Column(
        "posted_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("posted_by", UUID, nullable=True),
    UniqueConstraint("document_type", "document_id", name="uq_stock_postings_document"),
    Index("ix_stock_postings_org_unit_posted_at", "org_unit_id", "posted_at"),
    schema=DATABASE_SCHEMA,
)


RECEIPTS_TABLE = Table(
    "receipts",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("org_unit_id", UUID, nullable=False),
    Column("supplier_name", String(255), nullable=True),
    Column("supplier_document_number", String(64), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_receipts_org_unit_occurred_at", "org_unit_id", "occurred_at"),
    Index("ix_receipts_status", "status"),
    schema=DATABASE_SCHEMA,
)


RECEIPT_LINES_TABLE = Table(
    "receipt_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "receipt_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.receipts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("nomenclature_id", UUID, nullable=False),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("lot_code", String(64), nullable=True),
    Column("expires_at", Date, nullable=True),
    Column("quantity", QUANTITY, nullable=False),
    Column("unit_cost", Numeric(18, 6), nullable=False, server_default="0"),
    Column("total_cost", BigInteger, nullable=False, server_default="0"),
    CheckConstraint("quantity > 0", name="quantity_positive"),
    Index("ix_receipt_lines_receipt_id", "receipt_id"),
    schema=DATABASE_SCHEMA,
)


WRITE_OFFS_TABLE = Table(
    "write_offs",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("org_unit_id", UUID, nullable=False),
    Column("reason", String(255), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_write_offs_org_unit_occurred_at", "org_unit_id", "occurred_at"),
    Index("ix_write_offs_status", "status"),
    schema=DATABASE_SCHEMA,
)


WRITE_OFF_LINES_TABLE = Table(
    "write_off_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "write_off_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.write_offs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("nomenclature_id", UUID, nullable=False),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("lot_code", String(64), nullable=True),
    Column("quantity", QUANTITY, nullable=False),
    CheckConstraint("quantity > 0", name="quantity_positive"),
    Index("ix_write_off_lines_write_off_id", "write_off_id"),
    schema=DATABASE_SCHEMA,
)


STOCK_MOVEMENTS_TABLE = Table(
    "stock_movements",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column(
        "recorded_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("org_unit_id", UUID, nullable=False),
    Column("nomenclature_id", UUID, nullable=False),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("movement_type", String(32), nullable=False),
    Column("quantity", QUANTITY, nullable=False),
    Column("total_cost", BigInteger, nullable=False),
    Column(
        "posting_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_postings.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("created_by", UUID, nullable=True),
    CheckConstraint("quantity <> 0", name="quantity_non_zero"),
    CheckConstraint(
        "(quantity > 0 AND total_cost >= 0) OR (quantity < 0 AND total_cost <= 0)",
        name="sign_consistent",
    ),
    Index(
        "ix_stock_movements_org_unit_nomenclature",
        "org_unit_id",
        "nomenclature_id",
        "occurred_at",
    ),
    Index("ix_stock_movements_posting_id", "posting_id"),
    Index("ix_stock_movements_lot_id", "lot_id"),
    Index("ix_stock_movements_nomenclature_id", "nomenclature_id"),
    schema=DATABASE_SCHEMA,
)


STOCK_BALANCES_TABLE = Table(
    "stock_balances",
    metadata,
    Column("org_unit_id", UUID, primary_key=True),
    Column("nomenclature_id", UUID, primary_key=True),
    Column("quantity", QUANTITY, nullable=False, server_default="0"),
    Column("average_unit_cost", Numeric(18, 6), nullable=False, server_default="0"),
    Column("total_value", BigInteger, nullable=False, server_default="0"),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    CheckConstraint("total_value >= 0", name="total_value_non_negative"),
    schema=DATABASE_SCHEMA,
)


STOCK_LOT_BALANCES_TABLE = Table(
    "stock_lot_balances",
    metadata,
    Column("org_unit_id", UUID, primary_key=True),
    Column("nomenclature_id", UUID, primary_key=True),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("quantity", QUANTITY, nullable=False, server_default="0"),
    Column("total_value", BigInteger, nullable=False, server_default="0"),
    Column("average_unit_cost", Numeric(18, 6), nullable=False, server_default="0"),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    CheckConstraint("total_value >= 0", name="total_value_non_negative"),
    Index("ix_stock_lot_balances_lot_id", "lot_id"),
    schema=DATABASE_SCHEMA,
)


TRANSFERS_TABLE = Table(
    "transfers",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("from_org_unit_id", UUID, nullable=False),
    Column("to_org_unit_id", UUID, nullable=False),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_transfers_from_occurred_at", "from_org_unit_id", "occurred_at"),
    Index("ix_transfers_to_occurred_at", "to_org_unit_id", "occurred_at"),
    Index("ix_transfers_status", "status"),
    schema=DATABASE_SCHEMA,
)


TRANSFER_LINES_TABLE = Table(
    "transfer_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "transfer_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.transfers.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("nomenclature_id", UUID, nullable=False),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("lot_code", String(64), nullable=True),
    Column("quantity", QUANTITY, nullable=False),
    CheckConstraint("quantity > 0", name="transfer_lines_quantity_positive"),
    Index("ix_transfer_lines_transfer_id", "transfer_id"),
    schema=DATABASE_SCHEMA,
)


INVENTORY_COUNTS_TABLE = Table(
    "inventory_counts",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("org_unit_id", UUID, nullable=False),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index(
        "ix_inventory_counts_org_unit_occurred_at",
        "org_unit_id",
        "occurred_at",
    ),
    Index("ix_inventory_counts_status", "status"),
    schema=DATABASE_SCHEMA,
)


INVENTORY_COUNT_LINES_TABLE = Table(
    "inventory_count_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "inventory_count_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.inventory_counts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("nomenclature_id", UUID, nullable=False),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("lot_code", String(64), nullable=True),
    Column("counted_quantity", QUANTITY, nullable=False),
    CheckConstraint(
        "counted_quantity >= 0", name="counted_quantity_non_negative"
    ),
    Index(
        "ix_inventory_count_lines_inventory_count_id", "inventory_count_id"
    ),
    schema=DATABASE_SCHEMA,
)
