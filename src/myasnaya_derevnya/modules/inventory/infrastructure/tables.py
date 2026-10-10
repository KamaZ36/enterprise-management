from sqlalchemy import (
    BigInteger,
    Boolean,
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

# Количество — шесть знаков после запятой: граммы, миллилитры.
QUANTITY = Numeric(18, 6)


WAREHOUSES_TABLE = Table(
    "warehouses",
    metadata,
    Column("id", UUID, primary_key=True),
    # Орг-единица из модуля business: кросс-модульных FK в проекте нет,
    # существование проверяется приложением.
    Column("org_unit_id", UUID, nullable=False),
    Column("code", String(64), nullable=False),
    Column("name", String(255), nullable=False),
    Column("type", String(32), nullable=False),
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
    UniqueConstraint("code", name="uq_warehouses_code"),
    Index("ix_warehouses_org_unit_id", "org_unit_id"),
    schema=DATABASE_SCHEMA,
)


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
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "posted_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("posted_by", UUID, nullable=True),
    # Документы живут в своих таблицах, поэтому ссылка полиморфная. Зато
    # уникальность пары гарантирует, что документ проведён ровно один раз.
    UniqueConstraint("document_type", "document_id", name="uq_stock_postings_document"),
    Index("ix_stock_postings_warehouse_posted_at", "warehouse_id", "posted_at"),
    schema=DATABASE_SCHEMA,
)


RECEIPTS_TABLE = Table(
    "receipts",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("status", String(32), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("supplier_name", String(255), nullable=True),
    Column("supplier_document_number", String(64), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_receipts_warehouse_occurred_at", "warehouse_id", "occurred_at"),
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
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("reason", String(255), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_write_offs_warehouse_occurred_at", "warehouse_id", "occurred_at"),
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
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    ),
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
    # Знак суммы обязан совпадать со знаком количества: приход не может быть
    # отрицательным, расход — положительным.
    CheckConstraint(
        "(quantity > 0 AND total_cost >= 0) OR (quantity < 0 AND total_cost <= 0)",
        name="sign_consistent",
    ),
    Index(
        "ix_stock_movements_warehouse_nomenclature",
        "warehouse_id",
        "nomenclature_id",
        "occurred_at",
    ),
    Index("ix_stock_movements_posting_id", "posting_id"),
    Index("ix_stock_movements_lot_id", "lot_id"),
    schema=DATABASE_SCHEMA,
)


STOCK_BALANCES_TABLE = Table(
    "stock_balances",
    metadata,
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
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
    Column(
        "warehouse_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.warehouses.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("nomenclature_id", UUID, primary_key=True),
    Column(
        "lot_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.stock_lots.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("quantity", QUANTITY, nullable=False, server_default="0"),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    Index("ix_stock_lot_balances_lot_id", "lot_id"),
    schema=DATABASE_SCHEMA,
)
