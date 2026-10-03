from sqlalchemy import UUID, Boolean, Column, DateTime, String, Table, func

from myasnaya_derevnya.core.database import metadata

LOCATIONS_TABLE = Table(
    "locations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("location_type", String(20), nullable=False),
    Column("name", String(200), nullable=False),
    Column("code", String(50), nullable=False, unique=True),
    Column("address", String(300), nullable=True),
    Column("is_active", Boolean, nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    schema="organization",
)
