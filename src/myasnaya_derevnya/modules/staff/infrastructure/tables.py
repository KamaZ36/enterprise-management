from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
)

from myasnaya_derevnya.core.database import metadata

EMPLOYEES_TABLE = Table(
    "employees",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("user_id", UUID, ForeignKey("auth.users.id"), nullable=False),
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
    ),
    Index("ix_employees_last_name", "last_name"),
    schema="staff",
)

ROLES_TABLE = Table(
    "roles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String(64), nullable=False, unique=True),
    Column("name", String(128), nullable=False),
    Column("description", String(512), nullable=True),
    Column("level", Integer, nullable=False, server_default="0"),
    Column("is_system", Boolean, nullable=False, server_default="false"),
    Column("is_assignable", Boolean, nullable=False, server_default="true"),
    Column("is_wildcard", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    schema="staff",
)

ROLE_PERMISSIONS_TABLE = Table(
    "role_permissions",
    metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("staff.roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("permission_code", String(128), primary_key=True),
    schema="staff",
)

ROLE_GRANT_RULES_TABLE = Table(
    "role_grant_rules",
    metadata,
    Column(
        "granter_role_id",
        UUID(as_uuid=True),
        ForeignKey("staff.roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "grantable_role_id",
        UUID(as_uuid=True),
        ForeignKey("staff.roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    schema="staff",
)

ROLE_ASSIGNMENTS_TABLE = Table(
    "role_assignments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("staff.roles.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "org_unit_id",
        UUID(as_uuid=True),
        ForeignKey("business.org_units.id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("include_descendants", Boolean, nullable=False, server_default="true"),
    Column("status", String(32), nullable=False),
    Column(
        "granted_by_user_id",
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("granted_at", DateTime(timezone=True), nullable=False),
    Index("ix_role_assignments_user_active", "user_id", "status"),
    Index("ix_role_assignments_org_unit", "org_unit_id"),
    schema="staff",
)
