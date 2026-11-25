"""case-insensitive usernames

Логины сотрудников теперь ФИО на русском, поэтому поиск при входе не должен
зависеть от регистра. Уникальность тоже проверяем без учёта регистра, чтобы
не появилось двух «Струк Елена Николаевна» и «струк елена николаевна».

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-11-25 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "auth"
INDEX_NAME = "uq_user_identities_identifier_lower"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "user_identities",
        ["identity_type", sa.text("lower(identifier)")],
        unique=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="user_identities", schema=SCHEMA)
