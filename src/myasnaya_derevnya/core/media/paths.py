from pathlib import Path

from myasnaya_derevnya.core.settings import PROJECT_ROOT
from myasnaya_derevnya.core.settings.media import MediaSettings


def media_root(settings: MediaSettings) -> Path:
    root = Path(settings.media_root)

    return root if root.is_absolute() else PROJECT_ROOT / root
