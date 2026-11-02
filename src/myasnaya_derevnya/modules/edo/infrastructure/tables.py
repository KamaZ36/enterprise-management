from sqlalchemy import Column, Date, DateTime, Index, String, Table, func
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "edo"

EDO_DOCUMENTS_TABLE = Table(
    "documents",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("org_unit_id", UUID, nullable=False),
    Column("external_id", String(128), nullable=True),
    Column("number", String(64), nullable=False),
    Column("doc_date", Date, nullable=True),
    Column("supplier_name", String(255), nullable=True),
    Column("supplier_inn", String(12), nullable=True),
    Column("delivery_address", String(512), nullable=True),
    Column("comment", String(512), nullable=True),
    Column("status", String(24), nullable=False, server_default="manual"),
    Column("created_by", UUID, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_edo_documents_org_unit_id", "org_unit_id"),
    Index("ix_edo_documents_number", "number"),
    Index("ix_edo_documents_external_id", "external_id"),
    schema=DATABASE_SCHEMA,
)
