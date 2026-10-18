import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import (
    UserStatus,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    OrgUnitType,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.customer.domain.entities.customer import (
    CustomerStatus,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
    SpecLineRole,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.payment import (
    PaymentMethod,
    PaymentStatus,
)
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
)

pytestmark = pytest.mark.db


EXPECTED = {
    ("auth", "user_credentials", "credential_type"): UserCredentialType,
    ("auth", "user_identities", "identity_type"): UserIdentityType,
    ("auth", "users", "status"): UserStatus,
    ("business", "org_units", "type"): OrgUnitType,
    ("catalog", "nomenclatures", "unit"): UnitOfMeasurement,
    ("customer", "customers", "status"): CustomerStatus,
    ("inventory", "receipts", "status"): DocumentStatus,
    ("inventory", "stock_movements", "movement_type"): MovementType,
    ("inventory", "stock_postings", "document_type"): DocumentType,
    ("inventory", "transfers", "status"): DocumentStatus,
    ("inventory", "write_offs", "status"): DocumentStatus,
    ("production", "tech_cards", "basis"): TechCardBasis,
    ("production", "tech_card_lines", "role"): SpecLineRole,
    ("production", "tech_card_lines", "loss_kind"): LossKind,
    ("production", "tech_card_lines", "output_kind"): OutputKind,
    ("production", "production_orders", "status"): ProductionOrderStatus,
    ("production", "production_order_lines", "role"): SpecLineRole,
    ("production", "production_order_lines", "loss_kind"): LossKind,
    ("production", "production_order_lines", "output_kind"): OutputKind,
    ("sales", "orders", "status"): OrderStatus,
    ("sales", "orders", "channel"): OrderChannel,
    ("sales", "orders", "fulfillment_type"): FulfillmentType,
    ("sales", "orders", "payment_method"): PaymentMethod,
    ("sales", "orders", "payment_status"): PaymentStatus,
    ("staff", "role_assignments", "status"): RoleAssignmentStatus,
}


async def test_every_enum_value_is_allowed_by_database(
    db_session: AsyncSession,
) -> None:
    for (schema, table, column), enum in EXPECTED.items():
        definition = await db_session.scalar(
            text(
                "select pg_get_constraintdef(oid) from pg_constraint "
                "where conname = :name and contype = 'c'"
            ),
            {"name": f"ck_{table}_{column}"},
        )

        assert definition is not None, f"нет ограничения на {schema}.{table}.{column}"

        for member in enum:
            assert f"'{member.value}'" in definition, (
                f"{enum.__name__}.{member.name} = {member.value!r} "
                f"не разрешён ограничением {schema}.{table}.{column}"
            )
