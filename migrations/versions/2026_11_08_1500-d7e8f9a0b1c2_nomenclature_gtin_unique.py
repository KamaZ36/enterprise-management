"""nomenclature gtin unique

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-11-08 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | Sequence[str] | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.create_index(
        "uq_nomenclatures_gtin",
        "nomenclatures",
        ["gtin"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("gtin IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_nomenclatures_gtin",
        table_name="nomenclatures",
        schema=SCHEMA,
    )
