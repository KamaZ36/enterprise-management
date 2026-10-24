from myasnaya_derevnya.modules.fiscal.presentation.api.v1.endpoints import (
    router,
)
from myasnaya_derevnya.modules.fiscal.presentation.api.v1.ofd_endpoints import (
    router as ofd_router,
)

router.include_router(ofd_router)

__all__ = ["router"]
