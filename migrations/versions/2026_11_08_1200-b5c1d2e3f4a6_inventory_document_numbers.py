"""inventory document numbers

Revision ID: b5c1d2e3f4a6
Revises: f4e5d6c7b8a9
Create Date: 2026-11-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5c1d2e3f4a6"
down_revision: str | Sequence[str] | None = "f4e5d6c7b8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "inventory"

NUMBERED_TABLES = (
    ("receipts", "uq_receipts_number"),
    ("write_offs", "uq_write_offs_number"),
    ("transfers", "uq_transfers_number"),
    ("inventory_counts", "uq_inventory_counts_number"),
)


def upgrade() -> None:
    op.create_table(
        "document_number_counters",
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("number_year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "document_type",
            "number_year",
            name=op.f("pk_document_number_counters"),
        ),
        schema=SCHEMA,
    )

    for table, constraint in NUMBERED_TABLES:
        op.add_column(
            table,
            sa.Column("number", sa.String(length=32), nullable=True),
            schema=SCHEMA,
        )
        op.create_unique_constraint(
            constraint, table, ["number"], schema=SCHEMA
        )


def downgrade() -> None:
    for table, constraint in NUMBERED_TABLES:
        op.drop_constraint(
            constraint, table, type_="unique", schema=SCHEMA
        )
        op.drop_column(table, "number", schema=SCHEMA)

    op.drop_table("document_number_counters", schema=SCHEMA)
