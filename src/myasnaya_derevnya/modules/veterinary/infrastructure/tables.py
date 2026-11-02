from sqlalchemy import Column, DateTime, Index, String, Table, func
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "veterinary"

VETERINARY_DOCUMENTS_TABLE = Table(
    "veterinary_documents",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("org_unit_id", UUID, nullable=False),
    Column("number", String(64), nullable=True),
    Column("guid", UUID, nullable=True),
    Column("batch_id", String(255), nullable=True),
    Column("product_item_guid", UUID, nullable=True),
    Column("source", String(16), nullable=False, server_default="manual"),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_veterinary_documents_org_unit_id", "org_unit_id"),
    Index("ix_veterinary_documents_guid", "guid"),
    Index("ix_veterinary_documents_number", "number"),
    schema=DATABASE_SCHEMA,
)
