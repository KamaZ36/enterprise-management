from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestLoginCodeCommand:
    phone: str


@dataclass(frozen=True, slots=True)
class LoginCustomerCommand:
    phone: str
    code: str
