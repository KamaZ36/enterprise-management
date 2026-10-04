from sqlalchemy import (
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
    Column("id", UUID, primary_key=True),
    Column("status", String(20), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    schema="auth",
)


USER_IDENTITIES_TABLE = Table(
    "user_identities",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id", UUID, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    ),
    Column("identity_type", String(50), nullable=False),
    Column("identifier", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    UniqueConstraint(
        "identity_type",
        "identifier",
        name="uq_user_identities_provider_identifier",
    ),
    Index(
        "ix_user_identities_user_id",
        "user_id",
    ),
    schema="auth",
)


USER_CREDENTIALS_TABLE = Table(
    "user_credentials",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id",
        UUID,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("credential_type", String(30), nullable=False),
    Column("secret", String(255), nullable=False),
    UniqueConstraint(
        "user_id", "credential_type", name="uq_user_credentials_user_credential_type"
    ),
    Index(
        "ix_user_credentials_user_id",
        "user_id",
    ),
    schema="auth",
)

USER_SESSIONS_TABLE = Table(
    "user_sessions",
    metadata,
    Column("id", UUID, primary_key=True),
    Column(
        "user_id",
        UUID,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_user_sessions_user_id", "user_id"),
    Index("ix_user_sessions_expires_at", "expires_at"),
    schema="auth",
)
