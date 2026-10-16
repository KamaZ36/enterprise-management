from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "production"

QUANTITY = Numeric(18, 6)
COEFFICIENT = Numeric(18, 6)


TECH_CARDS_TABLE = Table(
    "tech_cards",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("code", String(64), nullable=False),
    Column("version", Integer, nullable=False),
    Column("name", String(255), nullable=False),
    Column("basis", String(16), nullable=False),
    Column("valid_from", Date, nullable=True),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    UniqueConstraint("code", "version", name="uq_tech_cards_code_version"),
    Index("ix_tech_cards_code", "code"),
    schema=DATABASE_SCHEMA,
)


TECH_CARD_LINES_TABLE = Table(
    "tech_card_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "tech_card_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.tech_cards.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(16), nullable=False),
    Column("nomenclature_id", UUID, nullable=True),
    Column("quantity", QUANTITY, nullable=False),
    Column("loss_kind", String(16), nullable=True),
    Column("output_kind", String(16), nullable=True),
    Column("cost_coefficient", COEFFICIENT, nullable=True),
    Index("ix_tech_card_lines_tech_card_id", "tech_card_id"),
    schema=DATABASE_SCHEMA,
)


PRODUCTION_ORDERS_TABLE = Table(
    "production_orders",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "org_unit_id",
        UUID,
        nullable=False,
    ),
    Column(
        "tech_card_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.tech_cards.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("tech_card_code", String(64), nullable=False),
    Column("tech_card_version", Integer, nullable=False),
    Column("status", String(16), nullable=False, server_default="draft"),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("batch_count", QUANTITY, nullable=False),
    Column("comment", String(512), nullable=True),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("posted_at", DateTime(timezone=True), nullable=True),
    Index("ix_production_orders_org_unit_id", "org_unit_id"),
    Index("ix_production_orders_status", "status"),
    schema=DATABASE_SCHEMA,
)


PRODUCTION_ORDER_LINES_TABLE = Table(
    "production_order_lines",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "order_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.production_orders.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(16), nullable=False),
    Column("nomenclature_id", UUID, nullable=True),
    Column("loss_kind", String(16), nullable=True),
    Column("output_kind", String(16), nullable=True),
    Column("cost_coefficient", COEFFICIENT, nullable=True),
    Column("planned_quantity", QUANTITY, nullable=False),
    Column("actual_quantity", QUANTITY, nullable=False),
    Column("cost", BigInteger, nullable=True),
    Index("ix_production_order_lines_order_id", "order_id"),
    schema=DATABASE_SCHEMA,
)
