from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from myasnaya_derevnya.core.database import metadata

DATABASE_SCHEMA = "fiscal"

CASH_REGISTERS_TABLE = Table(
    "cash_registers",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("reg_number", String(16), nullable=True),
    Column("serial_number", String(32), nullable=True),
    Column("name", String(255), nullable=False),
    Column("fiscal_place", String(255), nullable=True),
    Column("model", String(128), nullable=True),
    Column("fn_number", String(32), nullable=True),
    Column("ffd_version", String(8), nullable=True),
    Column("company_id", UUID, nullable=True),
    Column("registered_at", DateTime(timezone=True), nullable=True),
    Column("deregistered_at", DateTime(timezone=True), nullable=True),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    Column("attributes", JSONB, nullable=False, server_default="{}"),
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
    UniqueConstraint("reg_number", name="uq_cash_registers_reg_number"),
    Index("ix_cash_registers_serial_number", "serial_number"),
    schema=DATABASE_SCHEMA,
)

CASH_REGISTER_BINDINGS_TABLE = Table(
    "cash_register_bindings",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "cash_register_id",
        UUID,
        ForeignKey("fiscal.cash_registers.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("org_unit_id", UUID, nullable=False),
    Column("effective_from", DateTime(timezone=True), nullable=False),
    Column("effective_to", DateTime(timezone=True), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint(
        "effective_to is null or effective_to > effective_from", name="period"
    ),
    Index("ix_cash_register_bindings_cash_register_id", "cash_register_id"),
    Index("ix_cash_register_bindings_org_unit_id", "org_unit_id"),
    Index(
        "uq_cash_register_bindings_open",
        "cash_register_id",
        unique=True,
        postgresql_where=text("effective_to is null"),
    ),
    schema=DATABASE_SCHEMA,
)
