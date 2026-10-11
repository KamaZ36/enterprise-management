from sqlalchemy.exc import IntegrityError

from myasnaya_derevnya.core.errors import ConflictError, UniqueViolationError

UNIQUE_VIOLATION = "23505"


def _original(exc: IntegrityError) -> object | None:
    orig = getattr(exc, "orig", None)
    return getattr(orig, "__cause__", None) or orig


def sqlstate(exc: IntegrityError) -> str | None:
    return getattr(_original(exc), "sqlstate", None)


def constraint_name(exc: IntegrityError) -> str | None:
    return getattr(_original(exc), "constraint_name", None)


def conflict_error(exc: IntegrityError) -> ConflictError:
    if sqlstate(exc) == UNIQUE_VIOLATION:
        return UniqueViolationError(constraint=constraint_name(exc))

    return ConflictError()
