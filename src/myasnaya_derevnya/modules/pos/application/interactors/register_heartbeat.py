import logging
from dataclasses import dataclass
from datetime import datetime

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.pos.application.dto import PosHeartbeatResult
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RegisterHeartbeatCommand:
    agent: PosAgent
    status: str
    pending_receipts: int
    last_success_at: datetime | None = None
    last_error: str | None = None
    hostname: str | None = None
    version: str | None = None


class RegisterHeartbeatInteractor:
    """Сохраняет отметку агента: он жив, столько чеков в очереди."""

    def __init__(
        self,
        agent_repository: PosAgentRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._agent_repository = agent_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: RegisterHeartbeatCommand) -> PosHeartbeatResult:
        command.agent.mark_heartbeat(
            status=command.status,
            pending_receipts=command.pending_receipts,
            last_success_at=command.last_success_at,
            last_error=command.last_error,
            hostname=command.hostname,
            version=command.version,
        )
        await self._agent_repository.save(command.agent)
        await self._transaction_manager.commit()

        logger.info(
            "Отметка агента сбора продаж DoKa",
            extra={
                "agent_id": str(command.agent.id),
                "source_id": str(command.agent.source_id),
                "status": command.agent.status.value,
                "pending_receipts": command.agent.pending_receipts,
            },
        )

        return PosHeartbeatResult(server_time=get_datetime_utc())
