from abc import ABC, abstractmethod


class LoginCodeSender(ABC):
    @abstractmethod
    async def send(self, identifier: str, code: str) -> None: ...
