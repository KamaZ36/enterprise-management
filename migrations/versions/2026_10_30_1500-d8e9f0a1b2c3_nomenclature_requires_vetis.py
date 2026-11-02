"""nomenclature requires vetis

Revision ID: d8e9f0a1b2c3
Revises: b1c2d3e4f5a6
Create Date: 2026-10-30 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8e9f0a1b2c3"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"
TABLE = "nomenclatures"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("requires_vetis", sa.Boolean(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, "requires_vetis", schema=SCHEMA)
