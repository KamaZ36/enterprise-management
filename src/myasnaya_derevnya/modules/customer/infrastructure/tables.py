from sqlalchemy import Column, DateTime, String, Table, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

CUSTOMERS_TABLE = Table(
    "customers",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("user_id", UUID, nullable=False),
    Column("first_name", String(255), nullable=True),
    Column("status", String(20), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    UniqueConstraint("user_id", name="uq_customers_user_id"),
    schema="customer",
)
