"""session token hash

Revision ID: e2f3a4b5c6d7
Revises: c3d4e5f6a7b9
Create Date: 2026-11-02 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "auth"


def upgrade() -> None:
    op.add_column(
        "user_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )

    # Старые токены — это UUID сессии. Бэкфиллим их хэши, чтобы уже выданные
    # сессии продолжили работать после перехода на непрозрачные токены.
    op.execute(
        "UPDATE auth.user_sessions "
        "SET token_hash = encode(sha256(convert_to(id::text, 'UTF8')), 'hex') "
        "WHERE token_hash IS NULL"
    )

    op.alter_column(
        "user_sessions",
        "token_hash",
        existing_type=sa.String(length=64),
        nullable=False,
        schema=SCHEMA,
    )
    op.create_unique_constraint(
        "uq_user_sessions_token_hash",
        "user_sessions",
        ["token_hash"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_user_sessions_token_hash",
        "user_sessions",
        type_="unique",
        schema=SCHEMA,
    )
    op.drop_column("user_sessions", "token_hash", schema=SCHEMA)
