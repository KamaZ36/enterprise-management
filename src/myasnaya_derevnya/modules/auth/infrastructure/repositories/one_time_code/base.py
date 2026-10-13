from abc import ABC, abstractmethod
from datetime import datetime

from myasnaya_derevnya.modules.auth.domain.entities.one_time_code import OneTimeCode


class OneTimeCodeRepository(ABC):
    @abstractmethod
    async def add(self, code: OneTimeCode) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_by_identifier(self, identifier: str) -> OneTimeCode | None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, code: OneTimeCode) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_identifier(self, identifier: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_created_since(self, identifier: str, since: datetime) -> int:
        raise NotImplementedError
