from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.auth.application.services.session_token import (
    hash_session_token,
)

pytestmark = pytest.mark.db


async def test_session_token_is_stored_only_as_hash(
    db_session: AsyncSession, admin_session_token: str
) -> None:
    stored = await db_session.scalar(
        text("select token_hash from auth.user_sessions where token_hash = :hash"),
        {"hash": hash_session_token(admin_session_token)},
    )

    assert stored == hash_session_token(admin_session_token)
    assert admin_session_token not in stored


async def test_legacy_uuid_token_still_authenticates(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_id = await db_session.scalar(
        text(
            "select user_id from auth.user_identities"
            " where identity_type = 'username' and identifier = :identifier"
        ),
        {"identifier": settings.initial_admin_username},
    )
    legacy_token = uuid4()

    await db_session.execute(
        text(
            "insert into auth.user_sessions"
            " (id, user_id, token_hash, expires_at, created_at)"
            " values (:id, :user_id, :token_hash, :expires_at, now())"
        ),
        {
            "id": legacy_token,
            "user_id": user_id,
            "token_hash": hash_session_token(str(legacy_token)),
            "expires_at": datetime.now(UTC) + timedelta(days=1),
        },
    )
    await db_session.commit()

    response = await client.get(
        "/api/staff/me",
        headers={"Authorization": f"Bearer {legacy_token}"},
    )

    assert response.status_code == 200, response.text
