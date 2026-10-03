from sqlalchemy import (
    UUID,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    func,
    text,
)

from myasnaya_derevnya.core.database import metadata

EMPLOYEES_TABLE = Table(
    "employees",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("user_id", UUID, ForeignKey("auth.users.id"), nullable=True),
    Column("first_name", String(100), nullable=False),
    Column("last_name", String(100), nullable=False),
    Column("middle_name", String(100), nullable=True),
    Column("phone", String(20), nullable=True),  # E.164
    Column("position", String(100), nullable=False),
    Column("hired_at", Date, nullable=False),
    Column("dismissed_at", Date, nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index(
        "uq_employees_user_id",
        "user_id",
        unique=True,
        postgresql_where=text("user_id IS NOT NULL"),
    ),
    Index("ix_employees_last_name", "last_name"),
)
