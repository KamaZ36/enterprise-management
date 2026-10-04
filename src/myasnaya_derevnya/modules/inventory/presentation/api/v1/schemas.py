from pydantic import BaseModel

from myasnaya_derevnya.modules.inventory.domain.entities.location import LocationType


class CreateLocationSchema(BaseModel):
    name: str
    location_type: LocationType
    address: str
