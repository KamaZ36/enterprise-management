from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleCommand,
    PostSaleInteractor,
    SaleLineCommand,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.sqlalchemy import (
    SQLAlchemyStockPostingRepository,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from tests.modules.inventory.helpers import build_interactors, build_posting

OCCURRED_AT = datetime(2026, 10, 24, 8, 2, 26, tzinfo=UTC)
DOKA_ORG_ID = "915612757914"
RECEIPT_GUID = "27DE775614AD4D17A482B578611C605C915612757914"
PRODUCT_GUID = "1A537BD80C2E404890CB98625DB13B3E"


class FakeInventoryAPI:
    """Настоящее списание по складу без HTTP-слоя inventory."""

    def __init__(self, session) -> None:
        preconditions, _, ledger = build_posting(session)
        self._post_sale = PostSaleInteractor(
            preconditions=preconditions,
            ledger=ledger,
        )
        self._posting_repository = SQLAlchemyStockPostingRepository(session)

    async def post_sale(
        self,
        *,
        document_id: UUID,
        org_unit_id: UUID,
        occurred_at: datetime,
        lines,
        posted_by: UUID | None = None,
    ) -> None:
        await self._post_sale(
            PostSaleCommand(
                document_id=document_id,
                org_unit_id=org_unit_id,
                occurred_at=occurred_at,
                lines=tuple(
                    SaleLineCommand(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                    )
                    for line in lines
                ),
                posted_by=posted_by,
            )
        )

    async def sale_posting_exists(self, document_id: UUID) -> bool:
        return await self._posting_repository.exists(
            document_type=DocumentType.SALE,
            document_id=document_id,
        )


class FakeProductionAPI:
    async def recipe_for_output(self, nomenclature_id: UUID, on_date):
        return None


def build_posting_service(session, repository) -> ReceiptPostingService:
    return ReceiptPostingService(
        receipt_repository=repository,
        inventory_api=FakeInventoryAPI(session),
        production_api=FakeProductionAPI(),
        transaction_manager=SQLAlchemyTransactionManager(session),
    )


async def receive(
    session,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    unit_cost: str,
) -> None:
    interactors = build_interactors(session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            supplier_name="Поставщик",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))
