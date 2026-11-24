"""manual production orders

Задание может создаваться без техкарты: сырьё указывается вручную при
создании, выход — при проведении. Поэтому ссылка на техкарту становится
необязательной.

Revision ID: f1a2b3c4d5e6
Revises: e8f9a0b1c2d3
Create Date: 2026-11-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "production"


def upgrade() -> None:
    op.alter_column(
        "production_orders",
        "tech_card_id",
        existing_type=sa.UUID(),
        nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "production_orders",
        "tech_card_code",
        existing_type=sa.String(length=64),
        nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "production_orders",
        "tech_card_version",
        existing_type=sa.Integer(),
        nullable=True,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.production_orders "
            "WHERE tech_card_id IS NULL"
        )
    )
    op.alter_column(
        "production_orders",
        "tech_card_version",
        existing_type=sa.Integer(),
        nullable=False,
        schema=SCHEMA,
    )
    op.alter_column(
        "production_orders",
        "tech_card_code",
        existing_type=sa.String(length=64),
        nullable=False,
        schema=SCHEMA,
    )
    op.alter_column(
        "production_orders",
        "tech_card_id",
        existing_type=sa.UUID(),
        nullable=False,
        schema=SCHEMA,
    )
