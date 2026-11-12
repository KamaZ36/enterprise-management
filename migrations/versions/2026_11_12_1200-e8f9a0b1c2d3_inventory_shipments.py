"""inventory shipments

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-11-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e8f9a0b1c2d3"
down_revision: str | Sequence[str] | None = "d7e8f9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "inventory"

MOVEMENT_TYPES = (
    "receipt",
    "issue",
    "write_off",
    "shipment",
    "sale",
    "transfer_out",
    "transfer_in",
    "inventory_surplus",
    "inventory_shortage",
    "production_out",
    "production_in",
    "opening_balance",
)

DOCUMENT_TYPES = (
    "receipt",
    "write_off",
    "shipment",
    "transfer",
    "inventory_count",
    "production",
    "sale",
    "opening_balance",
)


def _values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_unit_id", UUID(), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("created_by", UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shipments")),
        sa.UniqueConstraint("number", name=op.f("uq_shipments_number")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_shipments_org_unit_occurred_at",
        "shipments",
        ["org_unit_id", "occurred_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_shipments_status",
        "shipments",
        ["status"],
        schema=SCHEMA,
    )

    op.create_table(
        "shipment_lines",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("shipment_id", UUID(), nullable=False),
        sa.Column("nomenclature_id", UUID(), nullable=False),
        sa.Column("lot_id", UUID(), nullable=True),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_shipment_lines_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"],
            [f"{SCHEMA}.shipments.id"],
            name=op.f("fk_shipment_lines_shipment_id_shipments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lot_id"],
            [f"{SCHEMA}.stock_lots.id"],
            name=op.f("fk_shipment_lines_lot_id_stock_lots"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shipment_lines")),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_shipment_lines_shipment_id",
        "shipment_lines",
        ["shipment_id"],
        schema=SCHEMA,
    )

    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        sa.text(f"movement_type IN ({_values(MOVEMENT_TYPES)})"),
        schema=SCHEMA,
    )

    op.drop_constraint(
        "document_type",
        "stock_postings",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "document_type",
        "stock_postings",
        sa.text(f"document_type IN ({_values(DOCUMENT_TYPES)})"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(
        "document_type",
        "stock_postings",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "document_type",
        "stock_postings",
        sa.text(
            "document_type IN "
            f"({_values(tuple(t for t in DOCUMENT_TYPES if t != 'shipment'))})"
        ),
        schema=SCHEMA,
    )

    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        sa.text(
            "movement_type IN "
            f"({_values(tuple(t for t in MOVEMENT_TYPES if t != 'shipment'))})"
        ),
        schema=SCHEMA,
    )

    op.drop_index(
        "ix_shipment_lines_shipment_id",
        table_name="shipment_lines",
        schema=SCHEMA,
    )
    op.drop_table("shipment_lines", schema=SCHEMA)

    op.drop_index("ix_shipments_status", table_name="shipments", schema=SCHEMA)
    op.drop_index(
        "ix_shipments_org_unit_occurred_at",
        table_name="shipments",
        schema=SCHEMA,
    )
    op.drop_table("shipments", schema=SCHEMA)
