from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError


@dataclass(slots=True, eq=False)
class CustomerBlocked(ForbiddenError):
    def __str__(self) -> str:
        return "Доступ клиента заблокирован"
