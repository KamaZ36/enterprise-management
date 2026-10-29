import ast
import importlib
import pkgutil
from pathlib import Path

from starlette.requests import Request

import myasnaya_derevnya
from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.main import create_app

PACKAGE_DIR = Path(myasnaya_derevnya.__file__).parent


def _module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_DIR.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _presentation_modules() -> list[Path]:
    return sorted(
        path
        for path in (PACKAGE_DIR / "modules").rglob("*.py")
        if "presentation" in path.parts
    )


def _requested_interactors(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "get":
            continue
        if not isinstance(func.value, ast.Name) or func.value.id != "context":
            continue
        names.update(arg.id for arg in node.args if isinstance(arg, ast.Name))

    return names


def test_all_modules_import() -> None:
    broken = []
    for module in pkgutil.walk_packages(
        myasnaya_derevnya.__path__, "myasnaya_derevnya."
    ):
        try:
            importlib.import_module(module.name)
        except Exception as exc:  # noqa: BLE001
            broken.append(f"{module.name}: {type(exc).__name__}: {exc}")

    assert broken == []


def test_create_app_exposes_endpoints() -> None:
    app = create_app()

    assert len(app.openapi()["paths"]) > 0


def test_auth_endpoints_are_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/auth/login/password" in paths
    assert "/api/auth/logout" in paths


def test_revoke_role_endpoint_is_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/staff/employees/role-assignments/{assignment_id}" in paths


def test_employee_read_endpoints_are_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "get" in paths["/api/staff/employees"]
    assert "get" in paths["/api/staff/employees/{employee_id}"]


def test_read_endpoints_document_response_schema() -> None:
    paths = create_app().openapi()["paths"]
    responses = paths["/api/staff/employees"]["get"]["responses"]

    assert "200" in responses


def test_inventory_read_endpoints_document_response_schema() -> None:
    spec = create_app().openapi()
    paths = spec["paths"]

    balances = paths["/api/inventory/locations/{org_unit_id}/balances"]["get"]
    balance = paths[
        "/api/inventory/locations/{org_unit_id}/balances/{nomenclature_id}"
    ]["get"]

    assert balances["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BalanceListSchema"
    }
    assert balance["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BalanceSchema"
    }
    assert (
        "average_unit_cost"
        in spec["components"]["schemas"]["BalanceSchema"]["properties"]
    )


def test_paginated_endpoints_declare_window_bounds() -> None:
    spec = create_app().openapi()

    for path in ("/api/staff/employees", "/api/catalog/nomenclatures"):
        parameters = {
            item["name"]: item for item in spec["paths"][path]["get"]["parameters"]
        }

        assert parameters["limit"]["schema"]["minimum"] == 1
        assert parameters["limit"]["schema"]["maximum"] == 100
        assert parameters["limit"]["schema"]["default"] == 20
        assert parameters["offset"]["schema"]["minimum"] == 0


async def test_every_endpoint_interactor_is_registered() -> None:
    targets: list[tuple[str, str, type]] = []
    for path in _presentation_modules():
        module = importlib.import_module(_module_name(path))
        for name in _requested_interactors(path):
            obj = getattr(module, name, None)
            if isinstance(obj, type):
                targets.append((_module_name(path), name, obj))

    assert targets, "не найдено ни одного context.get(...) — тест ничего не проверяет"

    request = Request(
        scope={"type": "http", "headers": [], "method": "POST", "path": "/"}
    )
    broken = []
    async with container(context={Request: request}) as context:
        for module_name, name, obj in targets:
            try:
                await context.get(obj)
            except Exception as exc:  # noqa: BLE001
                broken.append(f"{module_name}.{name}: {type(exc).__name__}: {exc}")

    assert broken == []


def test_my_orders_list_uses_customer_schema() -> None:
    schema = create_app().openapi()
    response = schema["paths"]["/api/me/orders"]["get"]["responses"]["200"]
    ref = response["content"]["application/json"]["schema"]["$ref"]

    assert ref.endswith("/MyOrderListSchema")

    properties = schema["components"]["schemas"]["MyOrderListItemSchema"]["properties"]
    assert "customer_id" not in properties
