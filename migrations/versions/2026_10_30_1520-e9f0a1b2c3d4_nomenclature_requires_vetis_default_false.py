"""nomenclature requires vetis default false

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-10-30 15:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0a1b2c3d4"
down_revision: str | Sequence[str] | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"
TABLE = "nomenclatures"
COLUMN = "requires_vetis"


def upgrade() -> None:
    op.execute(
        f"UPDATE {SCHEMA}.{TABLE} SET {COLUMN} = false "
        f"WHERE {COLUMN} IS NULL"
    )
    op.alter_column(
        TABLE,
        COLUMN,
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        TABLE,
        COLUMN,
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
        schema=SCHEMA,
    )
