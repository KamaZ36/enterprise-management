import pytest
from httpx import AsyncClient

from myasnaya_derevnya.core.settings import settings

pytestmark = pytest.mark.db


async def test_password_login_is_rate_limited(client: AsyncClient) -> None:
    payload = {
        "username": settings.initial_admin_username,
        "password": "definitely-wrong-password",
    }

    for _ in range(settings.login_max_attempts):
        response = await client.post("/api/auth/login/password", json=payload)
        assert response.status_code == 401, response.text

    blocked = await client.post("/api/auth/login/password", json=payload)
    assert blocked.status_code == 429, blocked.text
    assert int(blocked.headers["Retry-After"]) > 0

    with_correct_password = await client.post(
        "/api/auth/login/password",
        json={
            "username": settings.initial_admin_username,
            "password": settings.initial_admin_password,
        },
    )
    assert with_correct_password.status_code == 429, with_correct_password.text
