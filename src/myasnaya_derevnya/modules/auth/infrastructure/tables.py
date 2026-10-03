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

# Импортируем таблицу локаций напрямую, чтобы использовать её колонку для связи модулей
from myasnaya_derevnya.modules.organization.infrastructure.tables import LOCATIONS_TABLE

# 1. Сначала объявляем независимые таблицы (базовые сущности)
USERS_TABLE = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("status", String(20), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    schema="auth",
)

ROLES_TABLE = Table(
    "roles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    Column("grants_all", Boolean, nullable=False),
    schema="auth",
)

# 2. Теперь объявляем зависимые таблицы, используя прямые ссылки на объекты колонок (.c.id)
USER_CREDENTIALS_TABLE = Table(
    "user_credentials",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(
            USERS_TABLE.c.id, ondelete="CASCADE"
        ),  # ◄ ИСПОЛЬЗУЕМ ОБЪЕКТ КОЛОНКИ ТАБЛИЦЫ
        nullable=False,
    ),
    Column("provider", String(30), nullable=False),
    Column("identifier", String(255), nullable=False),
    Column("password_hash", String(255), nullable=True),
    UniqueConstraint(
        "provider", "identifier", name="uq_user_credentials_provider_identifier"
    ),
    UniqueConstraint("user_id", "provider", name="uq_user_credentials_user_provider"),
    schema="auth",
)

USER_SESSIONS_TABLE = Table(
    "user_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(
            USERS_TABLE.c.id, ondelete="CASCADE"
        ),  # ◄ ИСПОЛЬЗУЕМ ОБЪЕКТ КОЛОНКИ ТАБЛИЦЫ
        nullable=False,
    ),
    Column("provider", String(30), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Index("ix_user_sessions_user_id", "user_id"),
    Index("ix_user_sessions_expires_at", "expires_at"),
    schema="auth",
)

USER_ROLES_TABLE = Table(
    "user_roles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey(USERS_TABLE.c.id, ondelete="CASCADE"),  # ◄ ОБЪЕКТ КОЛОНКИ
        nullable=False,
    ),
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey(ROLES_TABLE.c.id, ondelete="RESTRICT"),  # ◄ ОБЪЕКТ КОЛОНКИ
        nullable=False,
    ),
    Column(
        "location_id",
        UUID(as_uuid=True),
        ForeignKey(
            LOCATIONS_TABLE.c.id
        ),  # ◄ ИСПОЛЬЗУЕМ ИМПОРТИРОВАННЫЙ ОБЪЕКТ ИЗ ДРУГОГО МОДУЛЯ
        nullable=True,
    ),
    Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    Column(
        "created_by",
        UUID(as_uuid=True),
        ForeignKey(USERS_TABLE.c.id),  # ◄ ОБЪЕКТ КОЛОНКИ
        nullable=False,
    ),
    Index("ix_role_assignments_user_id", "user_id"),
    schema="auth",
)

ROLE_PERMISSIONS_TABLE = Table(
    "role_permissions",
    metadata,
    Column(
        "role_id",
        UUID(as_uuid=True),
        ForeignKey(ROLES_TABLE.c.id, ondelete="CASCADE"),  # ◄ ОБЪЕКТ КОЛОНКИ
        primary_key=True,
    ),
    Column("permission_code", String(100), primary_key=True),
    schema="auth",
)
