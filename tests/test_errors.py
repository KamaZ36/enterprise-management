import json
from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ProjectError,
    UnauthorizedError,
    UniqueViolationError,
    ValidationError,
)
from myasnaya_derevnya.main import api_exception_handler, create_app
from myasnaya_derevnya.modules.auth.application.errors import (
    IncorrectCredentials,
    UserNotFound,
)
from myasnaya_derevnya.modules.catalog.application.errors import (
    CategoryAlreadyExists,
    PriceListAlreadyExists,
)
from myasnaya_derevnya.modules.catalog.domain.errors import EmptyNameError
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound, RoleNotFound

CASES = [
    (DomainError(), 400),
    (EmptyNameError(), 400),
    (UnauthorizedError(), 401),
    (IncorrectCredentials(), 401),
    (ForbiddenError(), 403),
    (NotFoundError(), 404),
    (UserNotFound(uuid4()), 404),
    (RoleNotFound(uuid4()), 404),
    (EmployeeNotFound(), 404),
    (ValidationError(), 422),
    (ConflictError(), 409),
    (UniqueViolationError(constraint="uq_nomenclatures_sku"), 409),
    (CategoryAlreadyExists("Мясо"), 409),
    (PriceListAlreadyExists("Опт"), 409),
    (RuntimeError("внутренняя кухня"), 500),
]


@pytest.mark.parametrize(("exc", "expected"), CASES)
async def test_status_code_by_error_type(exc: Exception, expected: int) -> None:
    response = await api_exception_handler(None, exc)

    assert response.status_code == expected


async def test_project_error_response_has_error_name_and_message() -> None:
    response = await api_exception_handler(None, RoleNotFound(uuid4()))
    payload = json.loads(response.body)

    assert payload["error"] == "RoleNotFound"
    assert "message" in payload


async def test_unexpected_error_does_not_leak_details() -> None:
    response = await api_exception_handler(None, RuntimeError("внутренняя кухня"))

    assert response.status_code == 500
    assert "внутренняя кухня" not in response.body.decode("utf-8")


def test_project_error_is_registered_in_app() -> None:
    app = create_app()

    assert ProjectError in app.exception_handlers
