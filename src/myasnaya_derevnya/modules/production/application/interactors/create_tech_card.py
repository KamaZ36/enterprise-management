import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    InvalidTechCardLineError,
)
from myasnaya_derevnya.modules.production.domain.permissions import (
    MANAGE_TECH_CARDS,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
    SpecLineRole,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TechCardLineCommand:
    role: SpecLineRole
    quantity: Decimal
    nomenclature_id: UUID | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CreateTechCardCommand:
    code: str
    name: str
    basis: TechCardBasis
    lines: tuple[TechCardLineCommand, ...]
    valid_from: date | None = None
    comment: str | None = None


class CreateTechCardInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        tech_card_repository: TechCardRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._tech_card_repository = tech_card_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateTechCardCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=user_id, permission=MANAGE_TECH_CARDS
        )
        if not allowed:
            raise ForbiddenError()

        version = await self._tech_card_repository.next_version(command.code)

        tech_card = TechCard.create(
            code=command.code,
            name=command.name,
            basis=command.basis,
            lines=[self._line(line) for line in command.lines],
            version=version,
            valid_from=command.valid_from,
            comment=command.comment,
            created_by=user_id,
        )

        await self._tech_card_repository.add(tech_card)
        await self._transaction_manager.commit()

        logger.info(
            "Создана технологическая карта",
            extra={
                "tech_card_id": str(tech_card.id),
                "tech_card_code": tech_card.code,
                "version": version,
            },
        )

        return tech_card.id

    def _line(self, command: TechCardLineCommand) -> TechCardLine:
        if command.role is SpecLineRole.COMPONENT:
            if command.nomenclature_id is None:
                raise InvalidTechCardLineError("у компонента нет номенклатуры")

            return TechCardLine.component(
                nomenclature_id=command.nomenclature_id,
                quantity=command.quantity,
            )

        if command.role is SpecLineRole.OUTPUT:
            if command.nomenclature_id is None:
                raise InvalidTechCardLineError("у выхода нет номенклатуры")

            return TechCardLine.output(
                nomenclature_id=command.nomenclature_id,
                quantity=command.quantity,
                output_kind=command.output_kind or OutputKind.MAIN,
                cost_coefficient=command.cost_coefficient,
            )

        if command.role is SpecLineRole.LOSS:
            if command.loss_kind is None:
                raise InvalidTechCardLineError("у потерь не указан вид")

            return TechCardLine.loss(
                loss_kind=command.loss_kind,
                quantity=command.quantity,
            )

        raise InvalidTechCardLineError(f"неизвестная роль строки: {command.role}")
