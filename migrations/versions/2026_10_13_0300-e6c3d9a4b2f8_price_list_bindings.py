from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6c3d9a4b2f8"
down_revision: str | Sequence[str] | None = "d5b2c8f1a3e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.create_table(
        "price_list_bindings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("price_list_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["price_list_id"],
            [f"{SCHEMA}.price_lists.id"],
            name=op.f("fk_price_list_bindings_price_list_id_price_lists"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_list_bindings")),
        sa.UniqueConstraint(
            "org_unit_id", name="uq_price_list_bindings_org_unit"
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("price_list_bindings", schema=SCHEMA)
