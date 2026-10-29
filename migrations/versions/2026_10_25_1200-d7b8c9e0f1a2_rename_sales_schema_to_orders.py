"""rename sales schema to orders

Revision ID: d7b8c9e0f1a2
Revises: c5e6f7a8b9d0
Create Date: 2026-10-25 12:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d7b8c9e0f1a2"
down_revision: str | Sequence[str] | None = "c5e6f7a8b9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SCHEMA = "sales"
NEW_SCHEMA = "orders"


def upgrade() -> None:
    op.execute(f"ALTER SCHEMA {OLD_SCHEMA} RENAME TO {NEW_SCHEMA}")


def downgrade() -> None:
    op.execute(f"ALTER SCHEMA {NEW_SCHEMA} RENAME TO {OLD_SCHEMA}")
