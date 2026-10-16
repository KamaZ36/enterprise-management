from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
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

    Column("sort_order", Integer, nullable=False, server_default="0"),
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
    Index("ix_categories_parent_id", "parent_id"),
    schema=DATABASE_SCHEMA,
)


NOMENCLATURES_TABLE = Table(
    "nomenclatures",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("sku", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("unit", String(16), nullable=False),
    Column(
        "category_id",
        UUID,
        ForeignKey("catalog.categories.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("gtin", String(14), nullable=True),
    Column("image_url", String(512), nullable=True),
    Column("description", String(1024), nullable=True),
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
    Index("ix_nomenclatures_category_id", "category_id"),
    schema=DATABASE_SCHEMA,
)


PRICE_LISTS_TABLE = Table(
    "price_lists",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(128), nullable=False, unique=True),
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
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    UniqueConstraint(
        "nomenclature_id",
        "price_list_id",
        name="uq_prices_nomenclature_price_list",
    ),
    CheckConstraint("value >= 0", name="value_non_negative"),
    Index("ix_prices_nomenclature_id", "nomenclature_id"),
    Index("ix_prices_price_list_id", "price_list_id"),
    schema=DATABASE_SCHEMA,
)


PRICE_LIST_BINDINGS_TABLE = Table(
    "price_list_bindings",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("org_unit_id", UUID, nullable=False),
    Column(
        "price_list_id",
        UUID,
        ForeignKey(f"{DATABASE_SCHEMA}.price_lists.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint("org_unit_id", name="uq_price_list_bindings_org_unit"),
    schema=DATABASE_SCHEMA,
)
