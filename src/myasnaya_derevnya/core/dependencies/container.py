from dishka import make_async_container

from myasnaya_derevnya.core.dependencies.database import DatabaseProvider

container = make_async_container(DatabaseProvider())
