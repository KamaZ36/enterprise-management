from pathlib import Path

from myasnaya_derevnya.core.settings import PROJECT_ROOT, AppSettings, Settings
from myasnaya_derevnya.core.settings.base import BaseAppSettings
from myasnaya_derevnya.core.settings.cors import CorsSettings
from myasnaya_derevnya.core.settings.database import DatabaseSettings
from myasnaya_derevnya.core.settings.login_codes import LoginCodeSettings
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.core.settings.seed import InitSeedSettings

SETTINGS_CLASSES = (
    BaseAppSettings,
    Settings,
    AppSettings,
    DatabaseSettings,
    InitSeedSettings,
    LoginCodeSettings,
    MediaSettings,
    CorsSettings,
)


def test_every_settings_class_reads_the_project_env_file() -> None:
    expected = PROJECT_ROOT / ".env"

    for settings_class in SETTINGS_CLASSES:
        env_file = settings_class.model_config.get("env_file")

        assert env_file is not None, settings_class.__name__
        assert Path(env_file) == expected, settings_class.__name__


def test_env_file_path_is_absolute() -> None:
    for settings_class in SETTINGS_CLASSES:
        env_file = settings_class.model_config.get("env_file")

        assert env_file is not None, settings_class.__name__
        assert Path(env_file).is_absolute(), settings_class.__name__


def test_media_settings_read_media_values_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MEDIA_ROOT=/custom/media\n", encoding="utf-8")

    settings = MediaSettings(_env_file=env_file)

    assert settings.media_root == "/custom/media"
