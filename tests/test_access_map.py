import re
from pathlib import Path

from myasnaya_derevnya.core.permissions import all_permissions

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACCESS_MAP = PROJECT_ROOT / "frontend/apps/admin/app/utils/access.ts"


def test_frontend_access_map_uses_known_permissions() -> None:
    codes = set(re.findall(r'"([a-z_]+\.[a-z_.]+)"', ACCESS_MAP.read_text("utf-8")))

    assert len(codes) >= 10, f"похоже, карта не разобралась: {sorted(codes)}"

    unknown = codes - {permission.code for permission in all_permissions()}

    assert not unknown, (
        f"в карте фронта права, которых нет в реестре: {sorted(unknown)}"
    )
