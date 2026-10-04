from sqlalchemy import UUID, Boolean, Column, DateTime, String, Table

from myasnaya_derevnya.core.database import metadata

LOCATIONS_TABLE = Table(
    "locations",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(255), nullable=False),
    Column("location_type", nullable=False),
    Column("address", String(500), nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime, nullable=False),
    schema="business",
)
