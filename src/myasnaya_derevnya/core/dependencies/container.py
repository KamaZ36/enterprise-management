from dishka import make_async_container

from myasnaya_derevnya.core.dependencies.database import DatabaseProvider
from myasnaya_derevnya.core.dependencies.services import ServicesDepProvider
from myasnaya_derevnya.modules.auth.infrastructure.dependencies import AuthDepProvider
from myasnaya_derevnya.modules.business.infrastructure.dependencies import (
    BusinessDepProvider,
)
from myasnaya_derevnya.modules.catalog.infrastructure.dependencies import (
    CatalogDepProvider,
)
from myasnaya_derevnya.modules.customer.infrastructure.dependencies import (
    CustomerDepProvider,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.dependencies import (
    FiscalDepProvider,
)
from myasnaya_derevnya.modules.inventory.infrastructure.dependencies import (
    InventoryDepProvider,
)
from myasnaya_derevnya.modules.orders.infrastructure.dependencies import (
    OrdersDepProvider,
)
from myasnaya_derevnya.modules.pos.infrastructure.dependencies import PosDepProvider
from myasnaya_derevnya.modules.production.infrastructure.dependencies import (
    ProductionDepProvider,
)
from myasnaya_derevnya.modules.staff.infrastructure.dependencies import StaffDepProvider

container = make_async_container(
    DatabaseProvider(),
    ServicesDepProvider(),
    AuthDepProvider(),
    StaffDepProvider(),
    BusinessDepProvider(),
    CatalogDepProvider(),
    CustomerDepProvider(),
    FiscalDepProvider(),
    InventoryDepProvider(),
    ProductionDepProvider(),
    OrdersDepProvider(),
    PosDepProvider(),
)
