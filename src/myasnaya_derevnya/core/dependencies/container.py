from dishka import make_async_container

from myasnaya_derevnya.core.dependencies.database import DatabaseProvider
from myasnaya_derevnya.core.dependencies.interactors import InteractorDepProvider
from myasnaya_derevnya.core.dependencies.repositories import RepositoriesDepProvider
from myasnaya_derevnya.core.dependencies.services import ServicesDepProvider

container = make_async_container(
    DatabaseProvider(),
    InteractorDepProvider(),
    RepositoriesDepProvider(),
    ServicesDepProvider(),
)
