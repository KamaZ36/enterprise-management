from abc import ABC, abstractmethod


class PasswordService(ABC):
    @abstractmethod
    def hash_password(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool:
        raise NotImplementedError
