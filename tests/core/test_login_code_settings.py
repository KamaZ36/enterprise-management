
import pytest
from pydantic import ValidationError

from myasnaya_derevnya.core.settings.login_codes import LoginCodeSettings


def test_login_code_secret_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGIN_CODE_SECRET", raising=False)

    with pytest.raises(ValidationError):
        LoginCodeSettings(_env_file=None)


def test_login_code_secret_must_be_long_enough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGIN_CODE_SECRET", "short")

    with pytest.raises(ValidationError):
        LoginCodeSettings(_env_file=None)


def test_login_code_secret_accepts_long_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGIN_CODE_SECRET", "a" * 32)

    assert LoginCodeSettings(_env_file=None).login_code_secret == "a" * 32
