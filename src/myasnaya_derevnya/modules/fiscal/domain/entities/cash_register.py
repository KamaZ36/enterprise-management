from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register_binding import (
    CashRegisterBinding,
)
from myasnaya_derevnya.modules.fiscal.domain.errors import (
    AlreadyBoundError,
    BindingConflictError,
    InactiveCashRegisterError,
    NoOpenBindingError,
    RegNumberRequiredError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.utils import get_datetime_utc


class BindingPlan:
    """Что нужно сохранить при привязке: новую привязку и закрываемую."""

    def __init__(
        self,
        binding: CashRegisterBinding,
        closes: CashRegisterBinding | None,
    ) -> None:
        self._binding = binding
        self._closes = closes

    @property
    def binding(self) -> CashRegisterBinding:
        return self._binding

    @property
    def closes(self) -> CashRegisterBinding | None:
        return self._closes


class CashRegister:
    """Фискальный регистратор: справочник и история привязок к точкам."""

    def __init__(
        self,
        id: UUID,
        reg_number: RegNumber | None,
        serial_number: str | None,
        name: str | None,
        fiscal_place: str | None,
        model: str | None,
        fn_number: str | None,
        ffd_version: str | None,
        company_id: UUID | None,
        registered_at: datetime | None,
        deregistered_at: datetime | None,
        is_active: bool,
        attributes: dict,
        created_at: datetime,
        updated_at: datetime,
        bindings: list[CashRegisterBinding] | None = None,
    ) -> None:
        self._id = id
        self._reg_number = reg_number
        self._serial_number = serial_number
        self._fiscal_place = fiscal_place
        self._name = self._build_name(name)
        self._model = model
        self._fn_number = fn_number
        self._ffd_version = ffd_version
        self._company_id = company_id
        self._registered_at = registered_at
        self._deregistered_at = deregistered_at
        self._is_active = is_active
        self._attributes = attributes
        self._created_at = created_at
        self._updated_at = updated_at
        self._bindings = bindings if bindings is not None else []

    @classmethod
    def create(
        cls,
        *,
        name: str | None = None,
        reg_number: RegNumber | None = None,
        serial_number: str | None = None,
        fiscal_place: str | None = None,
        model: str | None = None,
        fn_number: str | None = None,
        ffd_version: str | None = None,
        company_id: UUID | None = None,
        registered_at: datetime | None = None,
        attributes: dict | None = None,
    ) -> CashRegister:
        now = get_datetime_utc()

        return cls(
            id=uuid7(),
            reg_number=reg_number,
            serial_number=serial_number,
            name=name,
            fiscal_place=fiscal_place,
            model=model,
            fn_number=fn_number,
            ffd_version=ffd_version,
            company_id=company_id,
            registered_at=registered_at,
            deregistered_at=None,
            is_active=True,
            attributes=attributes or {},
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def reg_number(self) -> RegNumber | None:
        return self._reg_number

    @property
    def serial_number(self) -> str | None:
        return self._serial_number

    @property
    def name(self) -> str:
        return self._name

    @property
    def fiscal_place(self) -> str | None:
        return self._fiscal_place

    @property
    def model(self) -> str | None:
        return self._model

    @property
    def fn_number(self) -> str | None:
        return self._fn_number

    @property
    def ffd_version(self) -> str | None:
        return self._ffd_version

    @property
    def company_id(self) -> UUID | None:
        return self._company_id

    @property
    def registered_at(self) -> datetime | None:
        return self._registered_at

    @property
    def deregistered_at(self) -> datetime | None:
        return self._deregistered_at

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def attributes(self) -> dict:
        return self._attributes

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def bindings(self) -> tuple[CashRegisterBinding, ...]:
        return tuple(self._bindings)

    @property
    def open_binding(self) -> CashRegisterBinding | None:
        for binding in self._bindings:
            if binding.is_open:
                return binding

        return None

    def binding_at(self, at: datetime) -> CashRegisterBinding | None:
        for binding in self._bindings:
            if binding.is_active_at(at):
                return binding

        return None

    def change_details(
        self,
        *,
        name: str | None,
        reg_number: RegNumber | None,
        serial_number: str | None,
        fiscal_place: str | None,
        model: str | None,
        fn_number: str | None,
        ffd_version: str | None,
        company_id: UUID | None,
        registered_at: datetime | None,
        attributes: dict,
    ) -> None:
        self._reg_number = reg_number
        self._serial_number = serial_number
        self._fiscal_place = fiscal_place
        self._name = self._build_name(name)
        self._model = model
        self._fn_number = fn_number
        self._ffd_version = ffd_version
        self._company_id = company_id
        self._registered_at = registered_at
        self._attributes = attributes
        self._updated_at = get_datetime_utc()

    def plan_binding(
        self,
        *,
        org_unit_id: UUID,
        effective_from: datetime,
    ) -> BindingPlan:
        if effective_from.tzinfo is None:
            raise TimezoneRequiredError()

        if not self._is_active:
            raise InactiveCashRegisterError(self._id)

        if self._reg_number is None:
            raise RegNumberRequiredError(self._id)

        open_binding = self.open_binding
        closes: CashRegisterBinding | None = None

        if open_binding is not None:
            if open_binding.effective_from > effective_from:
                raise BindingConflictError(self._id)

            if (
                open_binding.org_unit_id == org_unit_id
                and open_binding.effective_from <= effective_from
            ):
                raise AlreadyBoundError(self._id, org_unit_id)

            open_binding.close(effective_from)
            closes = open_binding

        binding = CashRegisterBinding.create(
            cash_register_id=self._id,
            org_unit_id=org_unit_id,
            effective_from=effective_from,
        )
        self._bindings.append(binding)

        return BindingPlan(binding=binding, closes=closes)

    def plan_unbind(self, effective_to: datetime) -> CashRegisterBinding:
        if effective_to.tzinfo is None:
            raise TimezoneRequiredError()

        binding = self.open_binding
        if binding is None:
            raise NoOpenBindingError(self._id)

        binding.close(effective_to)
        return binding

    def deactivate(self, at: datetime) -> CashRegisterBinding | None:
        if at.tzinfo is None:
            raise TimezoneRequiredError()

        closed: CashRegisterBinding | None = None
        open_binding = self.open_binding

        if open_binding is not None and at > open_binding.effective_from:
            open_binding.close(at)
            closed = open_binding

        self._is_active = False
        self._deregistered_at = at
        self._updated_at = get_datetime_utc()
        return closed

    def activate(self) -> None:
        self._is_active = True
        self._deregistered_at = None
        self._updated_at = get_datetime_utc()

    def _build_name(self, name: str | None) -> str:
        """Имя для отображения: своё, затем место в ОФД, затем РНМ."""
        for candidate in (name, self._fiscal_place):
            if candidate is not None and candidate.strip():
                return candidate.strip()

        if self._reg_number is not None:
            return f"ККТ {self._reg_number}"

        return "Касса"
