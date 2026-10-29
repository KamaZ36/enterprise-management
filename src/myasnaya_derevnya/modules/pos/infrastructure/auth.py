from dataclasses import dataclass

from fastapi import Request

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.pos.application.errors import (
    InvalidAgentCredentialsError,
    MissingAgentHeadersError,
    PosSourceInactiveError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import hash_api_key
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)


@dataclass(frozen=True, slots=True)
class AuthenticatedAgent:
    agent: PosAgent
    source: PosSource


class PosAgentAuthenticator:
    """Проверяет Bearer-ключ терминала и возвращает его источник."""

    def __init__(
        self,
        request: Request,
        agent_repository: PosAgentRepository,
        source_repository: PosSourceRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._request = request
        self._agent_repository = agent_repository
        self._source_repository = source_repository
        self._transaction_manager = transaction_manager

    async def authenticate(self) -> AuthenticatedAgent:
        raw_key = self._bearer_token()
        install_id = (self._request.headers.get("X-Install-Id") or "").strip()

        if not install_id:
            raise MissingAgentHeadersError()

        agent = await self._agent_repository.get_by_key_hash(hash_api_key(raw_key))
        if agent is None or not agent.is_active:
            raise InvalidAgentCredentialsError()

        if agent.install_id is not None and agent.install_id != install_id:
            raise InvalidAgentCredentialsError()

        if agent.install_id is None:
            agent.bind_install(install_id)

        agent.mark_seen(version=self._request.headers.get("X-Agent-Version"))
        await self._agent_repository.save(agent)
        await self._transaction_manager.commit()

        source = await self._source_repository.get_by_id(agent.source_id)
        if source is None:
            raise PosSourceNotFoundError(agent.source_id)
        if not source.is_active:
            raise PosSourceInactiveError(source.doka_org_id)

        return AuthenticatedAgent(agent=agent, source=source)

    def _bearer_token(self) -> str:
        authorization = self._request.headers.get("Authorization")
        if not authorization:
            raise MissingAgentHeadersError()

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise MissingAgentHeadersError()

        return token.strip()
