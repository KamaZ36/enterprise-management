from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h7e6c3d9f2b4"
down_revision: str | Sequence[str] | None = "g6d5b2c8e4a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.add_column(
        "nomenclatures",
        sa.Column("image_url", sa.String(512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "nomenclatures",
        sa.Column("description", sa.String(1024), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("nomenclatures", "description", schema=SCHEMA)
    op.drop_column("nomenclatures", "image_url", schema=SCHEMA)
