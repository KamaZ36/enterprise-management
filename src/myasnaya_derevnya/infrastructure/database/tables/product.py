from sqlalchemy import Boolean, Column, String, Table
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.infrastructure.database.tables.base import metadata

PRODUCTS_TABLE = Table(
    "products",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("product_type", String(50), nullable=False),
    Column("unit", String(20), nullable=False),
    Column("sku", String(100), unique=True, nullable=False),
    Column("description", String, nullable=True),
    Column("active", Boolean, nullable=False),
)
