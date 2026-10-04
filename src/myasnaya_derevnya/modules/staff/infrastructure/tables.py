from sqlalchemy import (
    UUID,
    Boolean,
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
    Column("phone_number", String(20), nullable=True),  # E.164
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
    schema="staff",
)

USER_ROLES_TABLE = Table(
    "user_roles",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id",
        UUID,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "role_id",
        UUID,
        ForeignKey("staff.roles.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "location_id",
        UUID,
        # ForeignKey(LOCATIONS_TABLE.c.id),
        nullable=True,
    ),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "created_by",
        UUID,
        ForeignKey("auth.users.id"),
        nullable=False,
    ),
    Index("ix_role_assignments_user_id", "user_id"),
    schema="staff",
)

ROLE_PERMISSIONS_TABLE = Table(
    "role_permissions",
    metadata,
    Column(
        "role_id",
        UUID,
        ForeignKey("staff.roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("permission_code", String(100), primary_key=True),
    schema="staff",
)

ROLES_TABLE = Table(
    "roles",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("grants_all", Boolean, nullable=False),
    schema="staff",
)
