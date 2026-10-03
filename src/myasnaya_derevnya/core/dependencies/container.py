from dishka import make_async_container

from myasnaya_derevnya.core.dependencies.database import DatabaseProvider
from myasnaya_derevnya.core.dependencies.services import ServicesDepProvider
from myasnaya_derevnya.modules.auth.infrastructure.dependencies import AuthDepProvider
from myasnaya_derevnya.modules.organization.infrastructure.dependencies import (
    OrganizationDepProvidre,
)

container = make_async_container(
    DatabaseProvider(),
    ServicesDepProvider(),
    AuthDepProvider(),
    OrganizationDepProvidre(),
)
