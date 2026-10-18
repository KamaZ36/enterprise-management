from uuid import uuid4

from myasnaya_derevnya.core.logging.context import (
    get_request_id,
    get_user_id,
    reset_request_id,
    set_request_id,
    set_user_id,
)


def test_request_id_is_scoped_and_restored() -> None:
    assert get_request_id() is None

    token = set_request_id("req-1")
    assert get_request_id() == "req-1"

    reset_request_id(token)
    assert get_request_id() is None


def test_user_id_is_scoped() -> None:
    assert get_user_id() is None

    user_id = uuid4()
    set_user_id(user_id)
    assert get_user_id() == user_id

    set_user_id(None)
    assert get_user_id() is None
