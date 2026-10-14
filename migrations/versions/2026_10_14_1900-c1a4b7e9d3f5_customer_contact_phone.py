from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1a4b7e9d3f5"
down_revision: str | Sequence[str] | None = "b9f3a6d8c2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "customer"


def upgrade() -> None:
    # Контактный телефон отдельно от телефона-логина: по нему звонят, им не входят.
    op.add_column(
        "customers",
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("customers", "contact_phone", schema=SCHEMA)
