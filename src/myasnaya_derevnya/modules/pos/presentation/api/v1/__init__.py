from myasnaya_derevnya.modules.pos.presentation.api.v1.admin_endpoints import (
    router,
)
from myasnaya_derevnya.modules.pos.presentation.api.v1.agent_endpoints import (
    router as agent_router,
)

router.include_router(agent_router)

__all__ = ["router"]
