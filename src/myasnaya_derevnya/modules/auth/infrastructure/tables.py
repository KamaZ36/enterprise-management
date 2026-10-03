# auth/infrastructure/tables.py
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from myasnaya_derevnya.core.database import metadata

USERS_TABLE = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("status", String(20), nullable=False),  # UserStatus: "active", "blocked"...
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
)

USER_CREDENTIALS_TABLE = Table(
    "user_credentials",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("provider", String(30), nullable=False),  # "password", "phone_otp"
    Column("identifier", String(255), nullable=False),
    Column("password_hash", String(255), nullable=True),
    UniqueConstraint(
        "provider", "identifier", name="uq_user_credentials_provider_identifier"
    ),
    UniqueConstraint("user_id", "provider", name="uq_user_credentials_user_provider"),
)

USER_SESSIONS_TABLE = Table(
    "user_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("provider", String(30), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_user_sessions_user_id", "user_id"),
    Index("ix_user_sessions_expires_at", "expires_at"),
)

USER_ROLES_TABLE = Table(
    "user_roles",
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
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "location_id", UUID(as_uuid=True), ForeignKey("org.locations.id"), nullable=True
    ),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "created_by", UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=False
    ),
    Index("ix_role_assignments_user_id", "user_id"),
)

ROLES_TABLE = Table(
    "roles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("grants_all", Boolean, nullable=False),
)

ROLE_PERMISSIONS_TABLE = Table(
    "role_permissions",
    metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("permission_code", String(100), primary_key=True),
)
