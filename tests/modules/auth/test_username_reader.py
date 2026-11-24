from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.infrastructure.readers.username.sqlalchemy import (
    SQLAlchemyUsernameReader,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import (
    USER_IDENTITIES_TABLE,
    USERS_TABLE,
)

pytestmark = pytest.mark.db


async def test_returns_login_for_each_user(db_session: AsyncSession) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    login = f"user_{uuid4().hex[:10]}"
    phone = f"+79{uuid4().int % 10**9:09d}"

    await db_session.execute(
        insert(USERS_TABLE).values(
            [{"id": user_id, "status": "active"}, {"id": other_user_id, "status": "active"}]
        )
    )
    await db_session.execute(
        insert(USER_IDENTITIES_TABLE).values(
            [
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "identity_type": "username",
                    "identifier": login,
                },
                {
                    "id": uuid4(),
                    "user_id": other_user_id,
                    "identity_type": "phone_number",
                    "identifier": phone,
                },
            ]
        )
    )
    await db_session.commit()

    reader = SQLAlchemyUsernameReader(db_session)

    result = await reader.usernames_for_users([user_id, other_user_id])

    assert result == {user_id: login}


async def test_empty_request_returns_empty_mapping(db_session: AsyncSession) -> None:
    reader = SQLAlchemyUsernameReader(db_session)

    assert await reader.usernames_for_users([]) == {}
