from fastapi import APIRouter, Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.pos.application.errors import (
    AgentSourceMismatchError,
)
from myasnaya_derevnya.modules.pos.application.interactors.import_receipts import (
    ImportPosReceiptsCommand,
    ImportPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.register_heartbeat import (
    RegisterHeartbeatCommand,
    RegisterHeartbeatInteractor,
)
from myasnaya_derevnya.modules.pos.infrastructure.auth import PosAgentAuthenticator
from myasnaya_derevnya.modules.pos.presentation.api.v1.agent_schemas import (
    HeartbeatResultSchema,
    HeartbeatSchema,
    ImportPosReceiptsResultSchema,
    ImportPosReceiptsSchema,
)

router = APIRouter(tags=["Сбор продаж DoKa (агент)"])


@router.post(
    "/receipts",
    response_model=ImportPosReceiptsResultSchema,
    description="Принять пакет чеков из журнала продаж DoKa",
)
async def import_receipts(
    request: Request, data: ImportPosReceiptsSchema
) -> ImportPosReceiptsResultSchema:
    async with container(context={Request: request}) as context:
        authenticator = await context.get(PosAgentAuthenticator)
        authenticated = await authenticator.authenticate()

        if authenticated.source.doka_org_id != data.source.doka_org_id.strip():
            raise AgentSourceMismatchError(data.source.doka_org_id)

        command = ImportPosReceiptsCommand(
            source=authenticated.source,
            agent=authenticated.agent,
            file_name=data.file.name,
            file_sha256=data.file.sha256,
            exported_at=data.file.exported_at,
            receipts=tuple(receipt.to_dto() for receipt in data.receipts),
        )

        interactor = await context.get(ImportPosReceiptsInteractor)
        result = await interactor(command)

    return ImportPosReceiptsResultSchema.from_dto(result)


@router.post(
    "/heartbeat",
    response_model=HeartbeatResultSchema,
    description="Отметка агента: жив, столько чеков в очереди",
)
async def heartbeat(
    request: Request, data: HeartbeatSchema
) -> HeartbeatResultSchema:
    async with container(context={Request: request}) as context:
        authenticator = await context.get(PosAgentAuthenticator)
        authenticated = await authenticator.authenticate()

        if authenticated.source.doka_org_id != data.source.doka_org_id.strip():
            raise AgentSourceMismatchError(data.source.doka_org_id)

        command = RegisterHeartbeatCommand(
            agent=authenticated.agent,
            status=data.status,
            pending_receipts=data.pending_receipts,
            last_success_at=data.last_success_at,
            last_error=data.last_error,
            hostname=data.hostname,
            version=data.version,
        )

        interactor = await context.get(RegisterHeartbeatInteractor)
        result = await interactor(command)

    return HeartbeatResultSchema.from_dto(result)
