from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "catalog"

CATEGORIES_TABLE = Table(
    "categories",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "parent_id",
        UUID,
        ForeignKey("catalog.categories.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("name", String(128), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Index("ix_categories_parent_id", "parent_id"),
    schema=DATABASE_SCHEMA,
)


NOMENCLATURES_TABLE = Table(
    "nomenclatures",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("sku", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("type", String(32), nullable=False),
    Column("unit", String(16), nullable=False),
    Column(
        "category_id",
        UUID,
        ForeignKey("catalog.categories.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("gtin", String(14), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Index("ix_nomenclatures_category_id", "category_id"),
    Index("ix_nomenclatures_type", "type"),
    schema=DATABASE_SCHEMA,
)


PRICE_LISTS_TABLE = Table(
    "price_lists",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(128), nullable=False, unique=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=DATABASE_SCHEMA,
)


PRICES_TABLE = Table(
    "prices",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "nomenclature_id",
        UUID,
        ForeignKey("catalog.nomenclatures.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "price_list_id",
        UUID,
        ForeignKey("catalog.price_lists.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("value", BigInteger, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "nomenclature_id",
        "price_list_id",
        name="uq_prices_nomenclature_price_list",
    ),
    CheckConstraint("value >= 0", name="ck_prices_value_non_negative"),
    Index("ix_prices_nomenclature_id", "nomenclature_id"),
    Index("ix_prices_price_list_id", "price_list_id"),
    schema=DATABASE_SCHEMA,
)
