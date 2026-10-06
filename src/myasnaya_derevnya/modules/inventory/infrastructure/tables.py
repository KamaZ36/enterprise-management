from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
)

from myasnaya_derevnya.core.database import metadata

WAREHOUSES_TABLE = Table(
    "warehouses",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "org_unit_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("code", String(64), nullable=False),
    Column("name", String(255), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("org_unit_id", "code", name="uq_warehouses_org_unit_code"),
    Index("ix_warehouses_org_unit_id", "org_unit_id"),
    schema="inventory",
)
