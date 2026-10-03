from pydantic import BaseModel

from myasnaya_derevnya.modules.organization.domain.entities.location import LocationType


class CreateLocationCommandSchema(BaseModel):
    location_type: LocationType
    name: str
    code: str
    address: str | None
