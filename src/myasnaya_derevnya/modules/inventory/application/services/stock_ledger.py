from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot_balance import (
    StockLotBalance,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
    StockMovement,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_posting import (
    StockPosting,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
)
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import CostPolicy
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    BalanceKey,
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.base import (
    LotBalanceKey,
    StockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.base import (
    StockPostingRepository,
)


class StockLedger:
    """Единственная точка записи в остатки и журнал проводок."""

    def __init__(
        self,
        posting_repository: StockPostingRepository,
        movement_repository: StockMovementRepository,
        balance_repository: StockBalanceRepository,
        lot_balance_repository: StockLotBalanceRepository,
        cost_policy: CostPolicy,
    ) -> None:
        self._posting_repository = posting_repository
        self._movement_repository = movement_repository
        self._balance_repository = balance_repository
        self._lot_balance_repository = lot_balance_repository
        self._cost_policy = cost_policy

    @asynccontextmanager
    async def posting(
        self,
        *,
        document_type: str,
        document_id: UUID,
        warehouse_id: UUID,
        occurred_at: datetime,
        posted_by: UUID | None = None,
    ) -> AsyncIterator[StockPostingHandle]:
        # Запись проведения создаётся сразу: уникальность пары (тип, документ)
        # в базе не даст провести один документ дважды.
        posting = StockPosting.create(
            document_type=document_type,
            document_id=document_id,
            warehouse_id=warehouse_id,
            posted_by=posted_by,
        )
        try:
            await self._posting_repository.add(posting)
        except IntegrityError as exc:
            # Ограничение уникальности — источник истины для «проведён ровно
            # один раз»; переводим его в понятную ошибку. Транзакция после
            # этого откатывается провайдером сессии.
            raise DocumentAlreadyPostedError(document_id) from exc

        handle = StockPostingHandle(
            posting=posting,
            occurred_at=occurred_at,
            cost_policy=self._cost_policy,
            balance_repository=self._balance_repository,
            lot_balance_repository=self._lot_balance_repository,
            movement_repository=self._movement_repository,
        )

        yield handle

        await handle.flush()


class StockPostingHandle:
    """Операции одного проведения.

    Блокировки объявляются заранее и берутся пачкой в отсортированном
    порядке: ленивая блокировка в порядке строк документа даёт дедлоки.
    """

    def __init__(
        self,
        posting: StockPosting,
        occurred_at: datetime,
        cost_policy: CostPolicy,
        balance_repository: StockBalanceRepository,
        lot_balance_repository: StockLotBalanceRepository,
        movement_repository: StockMovementRepository,
    ) -> None:
        self._posting = posting
        self._occurred_at = occurred_at
        self._cost_policy = cost_policy
        self._balance_repository = balance_repository
        self._lot_balance_repository = lot_balance_repository
        self._movement_repository = movement_repository

        self._balances: dict[BalanceKey, StockBalance] = {}
        self._lot_balances: dict[LotBalanceKey, StockLotBalance] = {}
        self._movements: list[StockMovement] = []

    async def lock(
        self,
        *,
        balance_keys: Iterable[BalanceKey],
        lot_keys: Iterable[LotBalanceKey] = (),
    ) -> None:
        fresh = [key for key in balance_keys if key not in self._balances]
        if fresh:
            self._balances.update(await self._balance_repository.lock_many(fresh))

        fresh_lots = [key for key in lot_keys if key not in self._lot_balances]
        if fresh_lots:
            self._lot_balances.update(
                await self._lot_balance_repository.lock_many(fresh_lots)
            )

    async def receive(
        self,
        *,
        warehouse_id: UUID,
        nomenclature_id: UUID,
        quantity: Decimal,
        cost: Money,
        movement_type: MovementType,
        lot_id: UUID | None = None,
    ) -> None:
        balance = self._locked_balance(warehouse_id, nomenclature_id)
        balance.receive(quantity, cost)

        if lot_id is not None:
            self._locked_lot_balance(warehouse_id, nomenclature_id, lot_id).receive(
                quantity
            )

        self._movements.append(
            StockMovement.create(
                occurred_at=self._occurred_at,
                warehouse_id=warehouse_id,
                nomenclature_id=nomenclature_id,
                movement_type=movement_type,
                quantity=quantity,
                total_cost=cost,
                posting_id=self._posting.id,
                lot_id=lot_id,
                created_by=self._posting.posted_by,
            )
        )

    async def issue(
        self,
        *,
        warehouse_id: UUID,
        nomenclature_id: UUID,
        quantity: Decimal,
        movement_type: MovementType,
        lot_id: UUID | None = None,
    ) -> Money:
        balance = self._locked_balance(warehouse_id, nomenclature_id)
        cost = balance.issue(quantity, self._cost_policy)

        if lot_id is not None:
            self._locked_lot_balance(warehouse_id, nomenclature_id, lot_id).issue(
                quantity
            )

        self._movements.append(
            StockMovement.create(
                occurred_at=self._occurred_at,
                warehouse_id=warehouse_id,
                nomenclature_id=nomenclature_id,
                movement_type=movement_type,
                quantity=quantity,
                total_cost=cost,
                posting_id=self._posting.id,
                lot_id=lot_id,
                created_by=self._posting.posted_by,
            )
        )

        return cost

    async def flush(self) -> None:
        await self._movement_repository.add_many(self._movements)
        await self._balance_repository.save_many(list(self._balances.values()))

        if self._lot_balances:
            await self._lot_balance_repository.save_many(
                list(self._lot_balances.values())
            )

    def _locked_balance(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> StockBalance:
        key = (warehouse_id, nomenclature_id)
        balance = self._balances.get(key)
        if balance is None:
            raise RuntimeError(
                f"Баланс {key} не заблокирован: вызовите posting.lock(...) "
                "со всеми ключами документа до прихода и расхода"
            )
        return balance

    def _locked_lot_balance(
        self, warehouse_id: UUID, nomenclature_id: UUID, lot_id: UUID
    ) -> StockLotBalance:
        key = (warehouse_id, nomenclature_id, lot_id)
        lot_balance = self._lot_balances.get(key)
        if lot_balance is None:
            raise RuntimeError(
                f"Партионный остаток {key} не заблокирован: вызовите "
                "posting.lock(...) со всеми ключами документа"
            )
        return lot_balance
