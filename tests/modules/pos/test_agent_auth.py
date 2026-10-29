from uuid import uuid4

import pytest
from starlette.requests import Request

from myasnaya_derevnya.modules.pos.application.errors import (
    InvalidAgentCredentialsError,
    MissingAgentHeadersError,
    PosSourceInactiveError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import (
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)
from myasnaya_derevnya.modules.pos.infrastructure.auth import PosAgentAuthenticator


class FakeTransactionManager:
    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class FakeAgentRepository:
    def __init__(self, agent: PosAgent | None) -> None:
        self.agent = agent
        self.saved = []

    async def get_by_key_hash(self, api_key_hash: str) -> PosAgent | None:
        if self.agent is not None and self.agent.api_key_hash == api_key_hash:
            return self.agent
        return None

    async def save(self, agent: PosAgent) -> None:
        self.saved.append(agent)


class FakeSourceRepository:
    def __init__(self, source: PosSource | None) -> None:
        self.source = source

    async def get_by_id(self, source_id):
        if self.source is not None and self.source.id == source_id:
            return self.source
        return None


def make_request(
    *,
    authorization: str | None = "Bearer key",
    install_id: str | None = "install-1",
    version: str | None = "1.0.0",
) -> Request:
    headers: list[tuple[bytes, bytes]] = []

    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    if install_id is not None:
        headers.append((b"x-install-id", install_id.encode()))
    if version is not None:
        headers.append((b"x-agent-version", version.encode()))

    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


def build_agent(
    source_id,
    *,
    active: bool = True,
    bound: bool = True,
) -> tuple[PosAgent, str]:
    raw_key = generate_api_key()
    agent = PosAgent.create(
        source_id=source_id,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=api_key_prefix(raw_key),
        install_id="install-1" if bound else None,
    )
    if not active:
        agent.set_active(False)

    return agent, raw_key


def build_source(*, active: bool = True) -> PosSource:
    source = PosSource.create(
        doka_org_id="915612757914",
        name="Кафе",
        org_unit_id=uuid4(),
    )
    if not active:
        source.update(is_active=False)

    return source


def authenticator_for(
    agent: PosAgent | None,
    source: PosSource | None,
    *,
    authorization: str | None = "Bearer key",
    install_id: str | None = "install-1",
) -> PosAgentAuthenticator:
    return PosAgentAuthenticator(
        request=make_request(authorization=authorization, install_id=install_id),
        agent_repository=FakeAgentRepository(agent),
        source_repository=FakeSourceRepository(source),
        transaction_manager=FakeTransactionManager(),
    )


async def test_valid_key_returns_agent_and_source() -> None:
    source = build_source()
    agent, raw_key = build_agent(source.id)

    authenticated = await authenticator_for(
        agent, source, authorization=f"Bearer {raw_key}"
    ).authenticate()

    assert authenticated.agent.id == agent.id
    assert authenticated.source.id == source.id


async def test_unknown_install_is_bound_on_first_use() -> None:
    source = build_source()
    agent, raw_key = build_agent(source.id, bound=False)

    await authenticator_for(
        agent, source, authorization=f"Bearer {raw_key}"
    ).authenticate()

    assert agent.install_id == "install-1"


async def test_missing_headers_are_rejected() -> None:
    source = build_source()
    agent, raw_key = build_agent(source.id)

    with pytest.raises(MissingAgentHeadersError):
        await authenticator_for(
            agent, source, authorization=None
        ).authenticate()

    with pytest.raises(MissingAgentHeadersError):
        await authenticator_for(
            agent, source, authorization=f"Bearer {raw_key}", install_id=None
        ).authenticate()


async def test_wrong_key_or_inactive_agent_is_rejected() -> None:
    source = build_source()
    agent, _ = build_agent(source.id)

    with pytest.raises(InvalidAgentCredentialsError):
        await authenticator_for(
            agent, source, authorization="Bearer other"
        ).authenticate()

    inactive, raw_key = build_agent(source.id, active=False)
    with pytest.raises(InvalidAgentCredentialsError):
        await authenticator_for(
            inactive, source, authorization=f"Bearer {raw_key}"
        ).authenticate()


async def test_install_mismatch_is_rejected() -> None:
    source = build_source()
    agent, raw_key = build_agent(source.id)

    with pytest.raises(InvalidAgentCredentialsError):
        await authenticator_for(
            agent,
            source,
            authorization=f"Bearer {raw_key}",
            install_id="another-install",
        ).authenticate()


async def test_inactive_source_is_rejected() -> None:
    source = build_source(active=False)
    agent, raw_key = build_agent(source.id)

    with pytest.raises(PosSourceInactiveError):
        await authenticator_for(
            agent, source, authorization=f"Bearer {raw_key}"
        ).authenticate()


async def test_missing_source_is_rejected() -> None:
    source = build_source()
    agent, raw_key = build_agent(source.id)

    with pytest.raises(PosSourceNotFoundError):
        await authenticator_for(
            agent, None, authorization=f"Bearer {raw_key}"
        ).authenticate()
