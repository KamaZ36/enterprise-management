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
    """Имена, которые эндпоинт достаёт из контейнера: context.get(SomeInteractor)."""
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
    """Ловит битые импорты — приложение не должно падать на старте."""
    broken = []
    for module in pkgutil.walk_packages(
        myasnaya_derevnya.__path__, "myasnaya_derevnya."
    ):
        try:
            importlib.import_module(module.name)
        except Exception as exc:  # noqa: BLE001 - нужен любой сбой импорта
            broken.append(f"{module.name}: {type(exc).__name__}: {exc}")

    assert broken == []


def test_create_app_exposes_endpoints() -> None:
    app = create_app()

    assert len(app.openapi()["paths"]) > 0


def test_auth_endpoints_are_exposed() -> None:
    """Регресс: интерактор есть и зарегистрирован, но эндпоинт забыли подключить."""
    paths = create_app().openapi()["paths"]

    assert "/api/login/password" in paths
    assert "/api/logout" in paths


def test_revoke_role_endpoint_is_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/employees/roles/{assignment_id}" in paths


def test_employee_read_endpoints_are_exposed() -> None:
    paths = create_app().openapi()["paths"]

    assert "get" in paths["/api/employees"]
    assert "get" in paths["/api/employees/{employee_id}"]


def test_read_endpoints_document_response_schema() -> None:
    """Read-срез должен отдавать response-модель, а не пустую схему."""
    paths = create_app().openapi()["paths"]
    responses = paths["/api/employees"]["get"]["responses"]

    assert "200" in responses


async def test_every_endpoint_interactor_is_registered() -> None:
    """Регресс: интерактор, который эндпоинт резолвит, но забыт в DI-провайдере."""
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
            except Exception as exc:  # noqa: BLE001 - любая ошибка DI
                broken.append(f"{module_name}.{name}: {type(exc).__name__}: {exc}")

    assert broken == []
