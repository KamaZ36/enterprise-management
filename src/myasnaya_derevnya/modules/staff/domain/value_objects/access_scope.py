from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessScope:
    """Где действует право: вся компания или конкретный набор подразделений.

    Раньше это выражалось пустым значением в значении «вся компания» — соглашение,
    которое легко прочитать неверно. Теперь у него есть имя и явные проверки.
    """

    is_company_wide: bool = False
    org_unit_ids: frozenset[UUID] = field(default_factory=frozenset)

    @classmethod
    def company_wide(cls) -> AccessScope:
        return cls(is_company_wide=True)

    @classmethod
    def of(cls, org_unit_ids: Iterable[UUID]) -> AccessScope:
        return cls(org_unit_ids=frozenset(org_unit_ids))

    def is_empty(self) -> bool:
        return not self.is_company_wide and not self.org_unit_ids

    def covers(self, org_unit_id: UUID) -> bool:
        return self.is_company_wide or org_unit_id in self.org_unit_ids

    def narrow(self, org_unit_id: UUID | None) -> frozenset[UUID] | None:
        """Сузить область запрошенной точкой.

        Возвращает None, если фильтровать не нужно (вся компания), пустой набор —
        если запрошенная точка в область не входит, иначе — саму точку.
        """
        if org_unit_id is None:
            return None if self.is_company_wide else self.org_unit_ids

        return frozenset({org_unit_id}) if self.covers(org_unit_id) else frozenset()
