from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.production.application.dto import (
    TechCardDetail,
    TechCardLineItem,
)
from myasnaya_derevnya.modules.production.domain.errors import TechCardNotFoundError
from myasnaya_derevnya.modules.production.domain.permissions import READ_TECH_CARDS
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class GetTechCardInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        tech_card_repository: TechCardRepository,
        catalog_api: CatalogAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._tech_card_repository = tech_card_repository
        self._catalog_api = catalog_api

    async def __call__(self, tech_card_id: UUID) -> TechCardDetail:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=user_id, permission=READ_TECH_CARDS
        )
        if not allowed:
            raise ForbiddenError()

        tech_card = await self._tech_card_repository.get_by_id(tech_card_id)
        if tech_card is None:
            raise TechCardNotFoundError(tech_card_id)

        names = await self._catalog_api.nomenclature_names(
            [
                line.nomenclature_id
                for line in tech_card.lines
                if line.nomenclature_id is not None
            ]
        )

        return TechCardDetail(
            id=tech_card.id,
            code=tech_card.code,
            version=tech_card.version,
            name=tech_card.name,
            basis=tech_card.basis,
            created_at=tech_card.created_at,
            valid_from=tech_card.valid_from,
            comment=tech_card.comment,
            lines=[
                TechCardLineItem(
                    id=line.id,
                    role=line.role,
                    nomenclature_id=line.nomenclature_id,
                    nomenclature_name=names.get(line.nomenclature_id)
                    if line.nomenclature_id
                    else None,
                    quantity=line.quantity,
                    loss_kind=line.loss_kind,
                    output_kind=line.output_kind,
                    cost_coefficient=line.cost_coefficient,
                )
                for line in tech_card.lines
            ],
        )
