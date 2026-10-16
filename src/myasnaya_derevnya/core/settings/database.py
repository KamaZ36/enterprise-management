from myasnaya_derevnya.core.settings.base import BaseAppSettings


class DatabaseSettings(BaseAppSettings):
    db_user: str
    db_password: str
    db_host: str
    db_port: str
    db_database: str
    sql_echo: bool = False

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"
