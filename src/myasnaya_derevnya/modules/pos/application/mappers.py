from myasnaya_derevnya.modules.pos.application.dto import PosAgentItem
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent


def agent_item(agent: PosAgent) -> PosAgentItem:
    return PosAgentItem(
        id=agent.id,
        source_id=agent.source_id,
        install_id=agent.install_id,
        api_key_prefix=agent.api_key_prefix,
        hostname=agent.hostname,
        version=agent.version,
        status=agent.status.value,
        pending_receipts=agent.pending_receipts,
        last_seen_at=agent.last_seen_at,
        last_success_at=agent.last_success_at,
        last_error=agent.last_error,
        is_active=agent.is_active,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )
