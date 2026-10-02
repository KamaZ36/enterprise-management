from sqlalchemy import (
    UUID,
    Column,
    Date,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
)

from myasnaya_derevnya.infrastructure.database.tables.base import metadata

USERS_TABLE = Table(
    "users",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

USER_ROLES_TABLE = Table(
    "user_roles",
    metadata,
    Column(
        "user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("role_slug", String(50), primary_key=True),
)

CUSTOMER_PROFILES_TABLE = Table(
    "customer_profiles",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id",
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    ),
    Column("phone", String(20), nullable=False),
    Column("birth_date", Date, nullable=True),
)

EMPLOYEE_PROFILES_TABLE = Table(
    "employee_profiles",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id",
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    ),
    Column("first_name", String(100), nullable=False),
    Column("last_name", String(100), nullable=False),
)

USER_IDENTITIES_TABLE = Table(
    "user_identities",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("provider", String(20), nullable=False),
    Column("identifier", String(100), nullable=False),
    Column("password_hash", String(255), nullable=True),
    UniqueConstraint("provider", "identifier", name="uq_provider_identifier"),
)


USER_SESSIONS_TABLE = Table(
    "user_sessions",
    metadata,
    Column("token", UUID, primary_key=True),
    Column("user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("auth_provider", String(20), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
