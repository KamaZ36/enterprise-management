from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i8f7d4e0a3c5"
down_revision: str | Sequence[str] | None = "h7e6c3d9f2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("categories", "sort_order", schema=SCHEMA)
