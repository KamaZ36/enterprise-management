import logging
from uuid import uuid7

from myasnaya_derevnya.core.logging.context import (
    reset_request_id,
    set_request_id,
    set_user_id,
)
from myasnaya_derevnya.core.logging.filters import ContextFilter


def _record() -> logging.LogRecord:
    return logging.LogRecord(
        name="myasnaya_derevnya.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Событие",
        args=(),
        exc_info=None,
    )


def test_filter_stamps_request_and_user_ids() -> None:
    token = set_request_id("req-1")
    set_user_id(user_id := uuid7())

    record = _record()
    ContextFilter().filter(record)

    assert record.request_id == "req-1"  # type: ignore[attr-defined]
    assert record.user_id == str(user_id)  # type: ignore[attr-defined]

    reset_request_id(token)
    set_user_id(None)


def test_filter_omits_absent_context() -> None:
    record = _record()
    ContextFilter().filter(record)

    assert not hasattr(record, "request_id")
    assert not hasattr(record, "user_id")
