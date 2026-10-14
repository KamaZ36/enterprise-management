from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.production.domain.errors import (
    EmptyTechCardError,
    InvalidTechCardLineError,
    MainOutputRequiredError,
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
from myasnaya_derevnya.utils import get_datetime_utc


def _positive(quantity: Decimal) -> Decimal:
    if quantity <= 0:
        raise InvalidTechCardLineError("количество должно быть больше нуля")

    return quantity


@dataclass(frozen=True, slots=True)
class TechCardLine:
    id: UUID
    role: SpecLineRole
    quantity: Decimal
    nomenclature_id: UUID | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = None

    @classmethod
    def component(cls, *, nomenclature_id: UUID, quantity: Decimal) -> TechCardLine:
        return cls(
            id=uuid7(),
            role=SpecLineRole.COMPONENT,
            quantity=_positive(quantity),
            nomenclature_id=nomenclature_id,
        )

    @classmethod
    def output(
        cls,
        *,
        nomenclature_id: UUID,
        quantity: Decimal,
        output_kind: OutputKind = OutputKind.MAIN,
        cost_coefficient: Decimal | None = None,
    ) -> TechCardLine:
        if cost_coefficient is not None and cost_coefficient <= 0:
            raise InvalidTechCardLineError(
                "коэффициент распределения должен быть больше нуля"
            )

        return cls(
            id=uuid7(),
            role=SpecLineRole.OUTPUT,
            quantity=_positive(quantity),
            nomenclature_id=nomenclature_id,
            output_kind=output_kind,
            cost_coefficient=cost_coefficient,
        )

    @classmethod
    def loss(cls, *, loss_kind: LossKind, quantity: Decimal) -> TechCardLine:
        return cls(
            id=uuid7(),
            role=SpecLineRole.LOSS,
            quantity=_positive(quantity),
            loss_kind=loss_kind,
        )


class TechCard:
    def __init__(
        self,
        id: UUID,
        code: str,
        version: int,
        name: str,
        basis: TechCardBasis,
        created_at: datetime,
        lines: list[TechCardLine],
        created_by: UUID | None = None,
        valid_from: date | None = None,
        comment: str | None = None,
    ) -> None:
        self._id = id
        self._code = code
        self._version = version
        self._name = name
        self._basis = basis
        self._created_at = created_at
        self._lines = lines
        self._created_by = created_by
        self._valid_from = valid_from
        self._comment = comment

    @classmethod
    def create(
        cls,
        *,
        code: str,
        name: str,
        basis: TechCardBasis,
        lines: list[TechCardLine],
        version: int = 1,
        valid_from: date | None = None,
        comment: str | None = None,
        created_by: UUID | None = None,
    ) -> TechCard:
        code = code.strip()
        name = name.strip()

        if not code:
            raise InvalidTechCardLineError("код техкарты не может быть пустым")
        if not name:
            raise InvalidTechCardLineError("название техкарты не может быть пустым")
        if version < 1:
            raise InvalidTechCardLineError("версия начинается с единицы")

        components = [line for line in lines if line.role is SpecLineRole.COMPONENT]
        outputs = [line for line in lines if line.role is SpecLineRole.OUTPUT]

        if not components or not outputs:
            raise EmptyTechCardError()

        if basis is TechCardBasis.OUTPUT:
            main = [line for line in outputs if line.output_kind is OutputKind.MAIN]
            if len(main) != 1:
                raise MainOutputRequiredError()

        return cls(
            id=uuid7(),
            code=code,
            version=version,
            name=name,
            basis=basis,
            created_at=get_datetime_utc(),
            lines=list(lines),
            created_by=created_by,
            valid_from=valid_from,
            comment=comment,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def code(self) -> str:
        return self._code

    @property
    def version(self) -> int:
        return self._version

    @property
    def name(self) -> str:
        return self._name

    @property
    def basis(self) -> TechCardBasis:
        return self._basis

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def valid_from(self) -> date | None:
        return self._valid_from

    @property
    def comment(self) -> str | None:
        return self._comment

    @property
    def lines(self) -> list[TechCardLine]:
        return list(self._lines)

    @property
    def components(self) -> list[TechCardLine]:
        return [line for line in self._lines if line.role is SpecLineRole.COMPONENT]

    @property
    def outputs(self) -> list[TechCardLine]:
        return [line for line in self._lines if line.role is SpecLineRole.OUTPUT]

    @property
    def losses(self) -> list[TechCardLine]:
        return [line for line in self._lines if line.role is SpecLineRole.LOSS]

    @property
    def main_output(self) -> TechCardLine | None:
        return next(
            (line for line in self.outputs if line.output_kind is OutputKind.MAIN),
            None,
        )
