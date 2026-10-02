from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from myasnaya_derevnya.core.settings import settings

engine = create_async_engine(settings.db_url, echo=settings.sql_echo, future=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
