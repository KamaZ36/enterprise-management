from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

DATABASE_SCHEMA = "sales"

metadata = MetaData(schema=DATABASE_SCHEMA)

ORDERS_TABLE = Table(
    "orders",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("org_unit_id", UUID, nullable=False),
    Column("warehouse_id", UUID, nullable=True),
    Column("channel", String(16), nullable=False),
    Column("created_by", UUID, nullable=False),
    Column("customer_id", UUID, nullable=True),
    Column("status", String(16), nullable=False),
    Column("number", Integer, nullable=True),
    Column("day", Date, nullable=True),
    Column("planned_at", DateTime(timezone=True), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("contact_phone", String(32), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("cancelled_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("org_unit_id", "day", "number", name="uq_orders_number"),
    Index("ix_orders_org_unit_id", "org_unit_id"),
    Index("ix_orders_status", "status"),
    Index("ix_orders_customer_id", "customer_id"),
    schema=DATABASE_SCHEMA,
)

ORDER_LINES_TABLE = Table(
    "order_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "order_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.orders.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("nomenclature_id", UUID, nullable=False),
    Column("quantity", Numeric(18, 6), nullable=False),
    Column("unit_price", BigInteger, nullable=False),
    Column("cost_kopecks", BigInteger, nullable=True),
    Index("ix_order_lines_order_id", "order_id"),
    schema=DATABASE_SCHEMA,
)

ORDER_NUMBER_COUNTERS_TABLE = Table(
    "order_number_counters",
    metadata,
    Column("org_unit_id", UUID, primary_key=True),
    Column("day", Date, primary_key=True),
    Column("last_number", Integer, nullable=False),
    schema=DATABASE_SCHEMA,
)
