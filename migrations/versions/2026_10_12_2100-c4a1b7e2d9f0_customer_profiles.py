from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4a1b7e2d9f0"
down_revision: str | Sequence[str] | None = "56e522990993"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS customer")

    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customers")),
        sa.UniqueConstraint("user_id", name="uq_customers_user_id"),
        schema="customer",
    )


def downgrade() -> None:
    op.drop_table("customers", schema="customer")
