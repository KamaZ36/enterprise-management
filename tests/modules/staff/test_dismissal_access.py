from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def _create_employee(client: AsyncClient, org_unit_id: UUID) -> str:
    response = await client.post(
        "/api/staff/employees",
        json={
            "first_name": "Иван",
            "last_name": "Петров",
            "middle_name": None,
            "phone_number": None,
            "position": "Мясник",
            "hired_at": "2026-01-15",
            "org_unit_id": str(org_unit_id),
        },
    )
    assert response.status_code == 201, response.text

    return response.json()["employee_id"]


async def _create_credential(
    client: AsyncClient, employee_id: str
) -> tuple[str, str]:
    username = f"PYTEST-{uuid4().hex[:12]}"
    response = await client.post(
        "/api/staff/employees/credential",
        json={"employee_id": employee_id, "username": username},
    )
    assert response.status_code == 201, response.text

    return response.json()["username"], response.json()["password"]


async def _create_role(client: AsyncClient) -> str:
    response = await client.post(
        "/api/staff/employees/roles",
        json={
            "name": "Тестовая роль",
            "code": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "description": None,
            "level": 10,
            "is_system": False,
            "is_assignable": True,
            "is_wildcard": False,
            "permission_codes": ["inventory.balance.read"],
            "grantable_role_ids": [],
        },
    )
    assert response.status_code == 201, response.text

    return response.json()["role_id"]


async def _login(client: AsyncClient, username: str, password: str) -> str:
    response = await client.post(
        "/api/auth/login/password",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text

    return response.json()["session"]


async def _me(client: AsyncClient, token: str):
    return await client.get(
        "/api/staff/me", headers={"Authorization": f"Bearer {token}"}
    )


async def test_dismissal_revokes_sessions_and_roles(
    client: AsyncClient, db_session: AsyncSession, root_org_unit_id: UUID
) -> None:
    employee_id = await _create_employee(client, root_org_unit_id)
    username, password = await _create_credential(client, employee_id)

    user_id = await db_session.scalar(
        text("select user_id from staff.employees where id = :id"),
        {"id": employee_id},
    )
    assert user_id is not None

    role_id = await _create_role(client)
    assigned = await client.post(
        f"/api/staff/employees/{employee_id}/roles",
        json={
            "role_id": role_id,
            "org_unit_id": str(root_org_unit_id),
            "include_descendants": False,
        },
    )
    assert assigned.status_code == 201, assigned.text

    token = await _login(client, username, password)
    me = await _me(client, token)
    assert me.status_code == 200, me.text
    assert "inventory.balance.read" in me.json()["permissions"]

    dismissed = await client.patch(
        f"/api/staff/employees/{employee_id}", json={"is_active": False}
    )
    assert dismissed.status_code == 200, dismissed.text

    user_status = await db_session.scalar(
        text("select status from auth.users where id = :id"), {"id": user_id}
    )
    assert user_status == "blocked"

    assignment_status = await db_session.scalar(
        text("select status from staff.role_assignments where user_id = :id"),
        {"id": user_id},
    )
    assert assignment_status == "revoked"

    assert (await _me(client, token)).status_code == 401

    relogin = await client.post(
        "/api/auth/login/password",
        json={"username": username, "password": password},
    )
    assert relogin.status_code == 401, relogin.text

    restored = await client.patch(
        f"/api/staff/employees/{employee_id}", json={"is_active": True}
    )
    assert restored.status_code == 200, restored.text

    new_token = await _login(client, username, password)
    me_after = await _me(client, new_token)
    assert me_after.status_code == 200, me_after.text
    assert me_after.json()["permissions"] == []

    roles = await client.get(f"/api/staff/employees/{employee_id}/roles")
    assert roles.status_code == 200, roles.text
    assert roles.json() == []
