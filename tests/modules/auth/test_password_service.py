from myasnaya_derevnya.modules.auth.services.password_service import PasswordService

PASSWORD = "S3cret!pass"


def test_hash_is_not_plaintext() -> None:
    service = PasswordService()

    secret = service.hash(PASSWORD)

    assert secret != PASSWORD
    assert secret.startswith("$argon2")


def test_verify_accepts_correct_password() -> None:
    service = PasswordService()

    assert service.verify(PASSWORD, service.hash(PASSWORD)) is True


def test_verify_rejects_wrong_password() -> None:
    service = PasswordService()

    assert service.verify("wrong-password", service.hash(PASSWORD)) is False


def test_verify_rejects_garbage_hash() -> None:
    """Плейнтекст в колонке secret не должен приводить к исключению."""
    service = PasswordService()

    assert service.verify(PASSWORD, PASSWORD) is False


def test_hashes_are_salted() -> None:
    service = PasswordService()

    assert service.hash(PASSWORD) != service.hash(PASSWORD)
