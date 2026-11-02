"""production lot traceability

Revision ID: f3a4b5c6d7e8
Revises: e8c9d0f1a2b3
Create Date: 2026-10-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | Sequence[str] | None = "e8c9d0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "production"
TABLE = "production_order_lines"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("lot_id", sa.UUID(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        TABLE,
        sa.Column("expires_at", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_production_order_lines_lot_id",
        TABLE,
        ["lot_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_production_order_lines_lot_id",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.drop_column(TABLE, "expires_at", schema=SCHEMA)
    op.drop_column(TABLE, "lot_id", schema=SCHEMA)
