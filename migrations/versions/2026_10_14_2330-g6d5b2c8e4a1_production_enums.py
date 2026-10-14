from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g6d5b2c8e4a1"
down_revision: str | Sequence[str] | None = "e5c9a1b7d3f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INVENTORY_SCHEMA = "inventory"
PRODUCTION_SCHEMA = "production"

MOVEMENT_TYPES = (
    "receipt",
    "issue",
    "write_off",
    "sale",
    "transfer_out",
    "transfer_in",
    "inventory_surplus",
    "inventory_shortage",
    "production_out",
    "production_in",
)


PRODUCTION_CHECKS: dict[tuple[str, str], tuple[str, ...]] = {
    ("tech_cards", "basis"): ("input", "output"),
    ("tech_card_lines", "role"): ("component", "output", "loss"),
    ("tech_card_lines", "loss_kind"): (
        "shrinkage",
        "cooking",
        "trimming",
        "defrost",
        "defect",
    ),
    ("tech_card_lines", "output_kind"): ("main", "by_product"),
    ("production_orders", "status"): ("draft", "posted", "cancelled"),
    ("production_order_lines", "role"): ("component", "output", "loss"),
    ("production_order_lines", "loss_kind"): (
        "shrinkage",
        "cooking",
        "trimming",
        "defrost",
        "defect",
    ),
    ("production_order_lines", "output_kind"): ("main", "by_product"),
}


def _check(column: str, values: tuple[str, ...]) -> sa.TextClause:
    joined = ", ".join(f"'{value}'" for value in values)

    return sa.text(f"{column} IN ({joined})")


def upgrade() -> None:


    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=INVENTORY_SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        _check("movement_type", MOVEMENT_TYPES),
        schema=INVENTORY_SCHEMA,
    )

    for (table, column), values in PRODUCTION_CHECKS.items():
        op.create_check_constraint(
            column,
            table,
            _check(column, values),
            schema=PRODUCTION_SCHEMA,
        )


def downgrade() -> None:
    for table, column in PRODUCTION_CHECKS:
        op.drop_constraint(column, table, schema=PRODUCTION_SCHEMA, type_="check")

    op.drop_constraint(
        "movement_type",
        "stock_movements",
        schema=INVENTORY_SCHEMA,
        type_="check",
    )
    op.create_check_constraint(
        "movement_type",
        "stock_movements",
        _check("movement_type", MOVEMENT_TYPES[:8]),
        schema=INVENTORY_SCHEMA,
    )
