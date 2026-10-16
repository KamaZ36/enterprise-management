from myasnaya_derevnya.core.settings.base import BaseAppSettings


class InitSeedSettings(BaseAppSettings):
    initial_admin_username: str
    initial_admin_password: str
    admin_role_code: str
    admin_role_name: str
