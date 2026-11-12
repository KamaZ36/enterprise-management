from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.inventory.domain.entities.shipment import Shipment


class ShipmentRepository(ABC):
    @abstractmethod
    async def add(self, shipment: Shipment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, shipment: Shipment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, shipment_id: UUID) -> Shipment | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, shipment_id: UUID) -> None:
        raise NotImplementedError
