from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "56e522990993"
down_revision: str | Sequence[str] | None = "10e395367fc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "one_time_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_one_time_codes")),
        schema="auth",
    )
    op.create_index(
        "ix_one_time_codes_identifier",
        "one_time_codes",
        ["identifier"],
        unique=False,
        schema="auth",
    )
    op.create_index(
        "ix_one_time_codes_expires_at",
        "one_time_codes",
        ["expires_at"],
        unique=False,
        schema="auth",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_one_time_codes_expires_at", table_name="one_time_codes", schema="auth"
    )
    op.drop_index(
        "ix_one_time_codes_identifier", table_name="one_time_codes", schema="auth"
    )
    op.drop_table("one_time_codes", schema="auth")
