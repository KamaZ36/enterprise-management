from pydantic_settings import BaseSettings


class InitSeedSettings(BaseSettings):
    initial_admin_username: str
    initial_admin_password: str
    admin_role_code: str
    admin_role_name: str
