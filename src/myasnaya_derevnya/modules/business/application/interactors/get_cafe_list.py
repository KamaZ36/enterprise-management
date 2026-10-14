from myasnaya_derevnya.modules.business.application.dto import CafeOrgUnitListItem
from myasnaya_derevnya.modules.business.infrastructure.readers.org_unit.base import (
    OrgUnitReader,
)


class CafeListOrgUnitsInteractor:
    def __init__(self, org_unit_reader: OrgUnitReader) -> None:
        self._org_unit_reader = org_unit_reader

    async def __call__(self) -> list[CafeOrgUnitListItem]:
        cafe_list = await self._org_unit_reader.get_cafe_list()
        return cafe_list
