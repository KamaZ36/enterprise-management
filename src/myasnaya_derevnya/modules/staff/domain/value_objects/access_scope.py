from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccessScope:
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
        if org_unit_id is None:
            return None if self.is_company_wide else self.org_unit_ids

        return frozenset({org_unit_id}) if self.covers(org_unit_id) else frozenset()
