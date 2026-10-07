from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "business"

COMPANIES_TABLE = Table(
    "companies",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "org_unit_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    ),
    Column("code", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("inn", String(12), nullable=False),
    Column("kpp", String(9), nullable=False),
    Column("ogrn", String(15), nullable=False),
    Column("legal_address", String(512), nullable=False),
    Column("timezone", String(64), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("attributes", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema=DATABASE_SCHEMA,
)

ORG_UNITS_TABLE = Table(
    "org_units",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "parent_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("type", String(32), nullable=False),
    Column("code", String(64), nullable=False),
    Column("name", String(255), nullable=False),
    Column("address", String(512), nullable=True),
    Column("phone_number", String(32), nullable=True),
    Column("timezone", String(64), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("attributes", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("code", name="uq_org_units_code"),
    Index("ix_org_units_parent_id", "parent_id"),
    Index("ix_org_units_type", "type"),
    schema=DATABASE_SCHEMA,
)

ORG_UNIT_CLOSURE_TABLE = Table(
    "org_unit_closure",
    metadata,
    Column(
        "ancestor_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "descendant_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("depth", Integer, nullable=False),
    Index("ix_org_unit_closure_descendant", "descendant_id"),
    schema=DATABASE_SCHEMA,
)
