from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9f3a6d8c2e4"
down_revision: str | Sequence[str] | None = "a8e2f5c7b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sales"


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("orders", "contact_phone", schema=SCHEMA)
