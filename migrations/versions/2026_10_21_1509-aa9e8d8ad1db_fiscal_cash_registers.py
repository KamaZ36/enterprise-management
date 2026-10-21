"""fiscal cash registers

Revision ID: aa9e8d8ad1db
Revises: b4c5d6e7f8a9
Create Date: 2026-10-21 15:09:42.392088+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "aa9e8d8ad1db"
down_revision: str | Sequence[str] | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "fiscal"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "cash_registers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reg_number", sa.String(length=16), nullable=True),
        sa.Column("serial_number", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("fiscal_place", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("fn_number", sa.String(length=32), nullable=True),
        sa.Column("ffd_version", sa.String(length=8), nullable=True),
        sa.Column("company_id", sa.UUID(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deregistered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "attributes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_registers")),
        sa.UniqueConstraint("reg_number", name="uq_cash_registers_reg_number"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cash_registers_serial_number",
        "cash_registers",
        ["serial_number"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "cash_register_bindings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("org_unit_id", sa.UUID(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "effective_to is null or effective_to > effective_from",
            name=op.f("ck_cash_register_bindings_period"),
        ),
        sa.ForeignKeyConstraint(
            ["cash_register_id"],
            ["fiscal.cash_registers.id"],
            name=op.f(
                "fk_cash_register_bindings_cash_register_id_cash_registers"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cash_register_bindings")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cash_register_bindings_cash_register_id",
        "cash_register_bindings",
        ["cash_register_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_cash_register_bindings_org_unit_id",
        "cash_register_bindings",
        ["org_unit_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "uq_cash_register_bindings_open",
        "cash_register_bindings",
        ["cash_register_id"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("effective_to is null"),
    )


def downgrade() -> None:
    op.drop_table("cash_register_bindings", schema=SCHEMA)
    op.drop_table("cash_registers", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
