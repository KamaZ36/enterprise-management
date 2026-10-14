from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7d4e1b3c9a2"
down_revision: str | Sequence[str] | None = "e6c3d9a4b2f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINTS: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("auth", "user_credentials", "credential_type"): ("password",),
    ("auth", "user_identities", "identity_type"): ("username", "phone_number"),
    ("auth", "users", "status"): ("active", "blocked"),
    ("business", "org_units", "type"): ("root", "production", "group", "cafe", "shop"),
    ("catalog", "nomenclatures", "type"): (
        "raw_material",
        "semi_finished",
        "finished_good",
    ),
    ("catalog", "nomenclatures", "unit"): ("kg", "g", "pcs", "l", "m"),
    ("customer", "customers", "status"): ("active", "blocked"),
    ("inventory", "receipts", "status"): ("draft", "posted", "cancelled"),
    ("inventory", "stock_movements", "movement_type"): (
        "receipt",
        "issue",
        "write_off",
        "sale",
        "transfer_out",
        "transfer_in",
        "inventory_surplus",
        "inventory_shortage",
    ),
    ("inventory", "stock_postings", "document_type"): (
        "receipt",
        "write_off",
        "transfer",
        "inventory_count",
        "production",
    ),
    ("inventory", "transfers", "status"): ("draft", "posted", "cancelled"),
    ("inventory", "warehouses", "type"): ("raw", "production", "finished", "shop"),
    ("inventory", "write_offs", "status"): ("draft", "posted", "cancelled"),
    ("staff", "role_assignments", "status"): ("active", "revoked"),
}


def upgrade() -> None:
    for (schema, table, column), values in CONSTRAINTS.items():
        joined = ", ".join(f"'{value}'" for value in values)
        op.create_check_constraint(
            column,
            table,
            sa.text(f"{column} IN ({joined})"),
            schema=schema,
        )


def downgrade() -> None:
    for schema, table, column in CONSTRAINTS:
        op.drop_constraint(f"ck_{table}_{column}", table, schema=schema, type_="check")
