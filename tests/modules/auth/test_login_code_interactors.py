from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.modules.auth.application.errors import (
    InvalidPhoneNumber,
    LoginCodeAttemptsExceeded,
    LoginCodeExpired,
    LoginCodeHourlyLimitExceeded,
    LoginCodeInvalid,
    LoginCodeNotFound,
    LoginCodeRequestTooFrequent,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.ensure_user_by_phone import (
    EnsureUserByPhoneInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.request_login_code import (
    RequestLoginCodeInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.start_session import (
    StartSessionInteractor,
)
from myasnaya_derevnya.modules.auth.application.interactors.system.verify_login_code import (
    VerifyLoginCodeInteractor,
)
from myasnaya_derevnya.modules.auth.application.services.login_code_service import (
    LoginCodeService,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.one_time_code import OneTimeCode
from myasnaya_derevnya.utils import get_datetime_utc

PHONE = "+79991234567"
RAW_PHONE = "8 (999) 123-45-67"


class FakeUserRepository:
    def __init__(self) -> None:
        self.added: list = []

    async def add(self, user) -> None:
        self.added.append(user)

    async def save(self, user) -> None:
        return None

    async def get_by_id(self, user_id: UUID):
        return next((u for u in self.added if u.id == user_id), None)


class FakeIdentityRepository:
    def __init__(self) -> None:
        self.added: list[UserIdentity] = []

    async def add(self, user_identity: UserIdentity) -> None:
        self.added.append(user_identity)

    async def get_by_identifier_and_type(
        self, identifier: str, identity_type: UserIdentityType
    ) -> UserIdentity | None:
        return next(
            (
                i
                for i in self.added
                if i.identifier == identifier and i.identity_type is identity_type
            ),
            None,
        )

    async def save(self, user_identity: UserIdentity) -> None:
        return None


class FakeOneTimeCodeRepository:
    def __init__(self) -> None:
        self.codes: list[OneTimeCode] = []

    async def add(self, code: OneTimeCode) -> None:
        self.codes.append(code)

    async def get_latest_by_identifier(self, identifier: str) -> OneTimeCode | None:
        matching = [c for c in self.codes if c.identifier == identifier]

        if not matching:
            return None

        return max(matching, key=lambda c: c.created_at)

    async def update(self, code: OneTimeCode) -> None:
        return None

    async def delete_by_identifier(self, identifier: str) -> None:
        self.codes = [c for c in self.codes if c.identifier != identifier]

    async def count_created_since(self, identifier: str, since) -> int:
        return sum(
            1
            for c in self.codes
            if c.identifier == identifier and c.created_at >= since
        )


class FakeSessionRepository:
    def __init__(self) -> None:
        self.added: list = []

    async def add(self, user_session) -> None:
        self.added.append(user_session)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeLoginCodeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, identifier: str, code: str) -> None:
        self.sent.append((identifier, code))


def make_service(
    *,
    max_attempts: int = 3,
    min_interval: timedelta = timedelta(seconds=60),
    hourly_limit: int = 5,
) -> LoginCodeService:
    return LoginCodeService(
        secret="test-secret",
        code_length=6,
        ttl=timedelta(minutes=5),
        max_attempts=max_attempts,
        min_interval=min_interval,
        hourly_limit=hourly_limit,
    )


def build_request(*, service: LoginCodeService | None = None):
    codes = FakeOneTimeCodeRepository()
    sender = FakeLoginCodeSender()
    service = service or make_service()

    interactor = RequestLoginCodeInteractor(
        code_repository=codes,
        login_code_service=service,
        login_code_sender=sender,
        transaction_manager=FakeTransactionManager(),
    )

    return interactor, codes, sender, service


def build_verify(*, service: LoginCodeService | None = None):
    codes = FakeOneTimeCodeRepository()
    service = service or make_service()

    return VerifyLoginCodeInteractor(
        code_repository=codes, login_code_service=service
    ), codes


async def test_request_normalizes_phone_and_sends_code() -> None:
    interactor, codes, sender, service = build_request()

    await interactor(RAW_PHONE)

    assert len(codes.codes) == 1
    assert codes.codes[0].identifier == PHONE
    assert len(sender.sent) == 1
    assert sender.sent[0][0] == PHONE
    assert codes.codes[0].matches(service.hash(PHONE, sender.sent[0][1]))


async def test_request_rejects_invalid_phone() -> None:
    interactor, _, _, _ = build_request()

    with pytest.raises(InvalidPhoneNumber):
        await interactor("привет")


async def test_request_respects_min_interval() -> None:
    interactor, _, sender, _ = build_request()

    await interactor(PHONE)

    with pytest.raises(LoginCodeRequestTooFrequent):
        await interactor(PHONE)

    assert len(sender.sent) == 1


async def test_request_respects_hourly_limit() -> None:
    service = make_service(hourly_limit=2, min_interval=timedelta(seconds=0))
    interactor, codes, sender, _ = build_request(service=service)

    await interactor(PHONE)
    await interactor(PHONE)

    with pytest.raises(LoginCodeHourlyLimitExceeded):
        await interactor(PHONE)

    assert len(sender.sent) == 2


async def test_verify_accepts_code_and_consumes_it() -> None:
    service = make_service()
    codes = FakeOneTimeCodeRepository()
    codes.codes.append(
        OneTimeCode.create(
            identifier=PHONE,
            code_hash=service.hash(PHONE, "123456"),
            ttl=timedelta(minutes=5),
            max_attempts=3,
        )
    )
    interactor = VerifyLoginCodeInteractor(
        code_repository=codes, login_code_service=service
    )

    await interactor(PHONE, "123456")

    assert codes.codes == []


async def test_verify_rejects_wrong_code_and_counts_attempt() -> None:
    service = make_service()
    interactor, codes = build_verify(service=service)
    await RequestLoginCodeInteractor(
        code_repository=codes,
        login_code_service=service,
        login_code_sender=FakeLoginCodeSender(),
        transaction_manager=FakeTransactionManager(),
    )(PHONE)

    with pytest.raises(LoginCodeInvalid):
        await interactor(PHONE, "000000")

    assert codes.codes[0].attempts == 1


async def test_verify_rejects_exhausted_attempts() -> None:
    service = make_service(max_attempts=1)
    interactor, codes = build_verify(service=service)
    await RequestLoginCodeInteractor(
        code_repository=codes,
        login_code_service=service,
        login_code_sender=FakeLoginCodeSender(),
        transaction_manager=FakeTransactionManager(),
    )(PHONE)
    codes.codes[0].register_failed_attempt()

    with pytest.raises(LoginCodeAttemptsExceeded):
        await interactor(PHONE, "000000")


async def test_verify_drops_expired_code() -> None:
    service = make_service()
    interactor, codes = build_verify(service=service)
    codes.codes.append(
        OneTimeCode.create(
            identifier=PHONE,
            code_hash=service.hash(PHONE, "123456"),
            ttl=timedelta(seconds=-1),
            max_attempts=3,
        )
    )

    with pytest.raises(LoginCodeExpired):
        await interactor(PHONE, "123456")

    assert codes.codes == []


async def test_verify_without_code_raises_not_found() -> None:
    interactor, _ = build_verify()

    with pytest.raises(LoginCodeNotFound):
        await interactor(PHONE, "123456")


async def test_ensure_user_creates_user_and_identity_once() -> None:
    users = FakeUserRepository()
    identities = FakeIdentityRepository()
    interactor = EnsureUserByPhoneInteractor(
        user_repository=users, identity_repository=identities
    )

    user_id = await interactor(RAW_PHONE)
    same_user_id = await interactor(PHONE)

    assert len(users.added) == 1
    assert len(identities.added) == 1
    assert identities.added[0].identifier == PHONE
    assert identities.added[0].identity_type is UserIdentityType.PHONE_NUMBER
    assert user_id == same_user_id


async def test_ensure_user_rejects_invalid_phone() -> None:
    interactor = EnsureUserByPhoneInteractor(
        user_repository=FakeUserRepository(),
        identity_repository=FakeIdentityRepository(),
    )

    with pytest.raises(InvalidPhoneNumber):
        await interactor("не телефон")


async def test_start_session_creates_session_with_future_expiry() -> None:
    sessions = FakeSessionRepository()
    interactor = StartSessionInteractor(session_repository=sessions)
    user_id = uuid4()

    session_id = await interactor(user_id)

    assert len(sessions.added) == 1
    assert sessions.added[0].id == session_id
    assert sessions.added[0].user_id == user_id
    assert sessions.added[0].expires_at > get_datetime_utc()
