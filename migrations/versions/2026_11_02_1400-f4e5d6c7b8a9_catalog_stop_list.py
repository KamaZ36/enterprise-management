"""catalog stop list

Revision ID: f4e5d6c7b8a9
Revises: e2f3a4b5c6d7
Create Date: 2026-11-02 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4e5d6c7b8a9"
down_revision: str | Sequence[str] | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.create_table(
        "stop_list_entries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column(
            "nomenclature_id",
            sa.UUID(),
            sa.ForeignKey(
                "catalog.nomenclatures.id", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "org_unit_id",
            "nomenclature_id",
            name="uq_stop_list_entries_org_unit_nomenclature",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_stop_list_entries_nomenclature_id",
        "stop_list_entries",
        ["nomenclature_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stop_list_entries_nomenclature_id",
        table_name="stop_list_entries",
        schema=SCHEMA,
    )
    op.drop_table("stop_list_entries", schema=SCHEMA)
