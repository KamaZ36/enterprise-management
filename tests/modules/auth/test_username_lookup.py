from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.auth.domain.entities.identity import UserIdentityType
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.sqlalchemy import (
    SQLAlchemyUserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.tables import (
    USER_IDENTITIES_TABLE,
    USERS_TABLE,
)

pytestmark = pytest.mark.db


async def test_username_lookup_ignores_case_and_spaces(
    db_session: AsyncSession,
) -> None:
    user_id = uuid4()
    suffix = uuid4().hex[:6]
    login = f"Струк Елена {suffix}"

    await db_session.execute(insert(USERS_TABLE).values(id=user_id, status="active"))
    await db_session.execute(
        insert(USER_IDENTITIES_TABLE).values(
            id=uuid4(),
            user_id=user_id,
            identity_type="username",
            identifier=login,
        )
    )
    await db_session.commit()

    repository = SQLAlchemyUserIdentityRepository(db_session)

    found = await repository.get_by_identifier_and_type(
        f"  струк   елена {suffix}  ", UserIdentityType.USERNAME
    )

    assert found is not None
    assert found.identifier == login
