from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2b5e8f0a4c6"
down_revision: str | Sequence[str] | None = "c1a4b7e9d3f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "staff"
ORG_SCHEMA = "business"


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("org_unit_id", sa.UUID(), nullable=True),
        schema=SCHEMA,
    )


    op.execute(
        """
        UPDATE staff.employees AS e
        SET org_unit_id = COALESCE(
            (
                SELECT ra.org_unit_id
                FROM staff.role_assignments AS ra
                WHERE ra.user_id = e.user_id
                  AND ra.status = 'active'
                  AND ra.org_unit_id IS NOT NULL
                ORDER BY ra.created_at
                LIMIT 1
            ),
            (SELECT id FROM business.org_units WHERE parent_id IS NULL LIMIT 1)
        )
        """
    )

    op.alter_column("employees", "org_unit_id", nullable=False, schema=SCHEMA)
    op.create_foreign_key(
        "fk_employees_org_unit_id",
        "employees",
        "org_units",
        ["org_unit_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=ORG_SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_employees_org_unit_id",
        "employees",
        ["org_unit_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employees_org_unit_id",
        table_name="employees",
        schema=SCHEMA,
    )
    op.drop_constraint(
        "fk_employees_org_unit_id",
        "employees",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.drop_column("employees", "org_unit_id", schema=SCHEMA)
