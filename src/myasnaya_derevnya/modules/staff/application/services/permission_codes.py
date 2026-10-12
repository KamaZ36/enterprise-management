from collections.abc import Iterable

from myasnaya_derevnya.core.permissions import all_permissions
from myasnaya_derevnya.modules.staff.domain.errors import UnknownPermissionError


def ensure_known_permissions(permission_codes: Iterable[str]) -> None:
    known = {permission.code for permission in all_permissions()}

    for code in sorted(permission_codes):
        if code not in known:
            raise UnknownPermissionError(code)
