"""index stock movements by nomenclature

Revision ID: f2b3c4d5e6a7
Revises: e1a2b3c4d5e6
Create Date: 2026-10-17 14:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f2b3c4d5e6a7"
down_revision: str | Sequence[str] | None = "e1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_stock_movements_nomenclature_id"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "stock_movements",
        ["nomenclature_id"],
        unique=False,
        schema="inventory",
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="stock_movements",
        schema="inventory",
    )
