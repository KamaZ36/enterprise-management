from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.pos.domain.entities.import_batch import PosImportBatch


class PosImportBatchRepository(ABC):
    @abstractmethod
    async def add(self, batch: PosImportBatch) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, batch: PosImportBatch) -> None:
        raise NotImplementedError
