import logging
from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.application.dto import (
    OfdBatchPostResult,
    OfdPostResult,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ofd_receipt import (
    PostOfdReceiptCommand,
    PostOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_MANAGE,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.base import (
    OfdReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)

MAX_BATCH = 100


@dataclass(frozen=True, slots=True)
class PostReadyOfdReceiptsCommand:
    limit: int = MAX_BATCH


class PostReadyOfdReceiptsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        receipt_reader: OfdReceiptReader,
        post_interactor: PostOfdReceiptInteractor,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._receipt_reader = receipt_reader
        self._post_interactor = post_interactor

    async def __call__(
        self, command: PostReadyOfdReceiptsCommand
    ) -> OfdBatchPostResult:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=CASH_REGISTER_RECEIPT_MANAGE
        )
        if scope.is_empty():
            raise ForbiddenError()

        items, _ = await self._receipt_reader.list(
            status="ready",
            reg_number=None,
            date_from=None,
            date_to=None,
            org_unit_ids=None if scope.is_company_wide else scope.org_unit_ids,
            limit=min(max(command.limit, 1), MAX_BATCH),
            offset=0,
        )

        results: list[OfdPostResult] = []
        for item in items:
            try:
                results.append(
                    await self._post_interactor(
                        PostOfdReceiptCommand(receipt_id=item.id)
                    )
                )
            except Exception as exc:  # noqa: BLE001 — ошибка одного чека не отменяет пакет
                logger.warning(
                    "Чек ОФД не проведён пакетной операцией",
                    extra={"receipt_id": str(item.id), "error": str(exc)},
                )
                results.append(
                    OfdPostResult(
                        receipt_id=item.id, status="failed", error=str(exc)
                    )
                )

        posted = sum(1 for result in results if result.status == "posted")
        return OfdBatchPostResult(
            posted=posted,
            failed=len(results) - posted,
            results=tuple(results),
        )
