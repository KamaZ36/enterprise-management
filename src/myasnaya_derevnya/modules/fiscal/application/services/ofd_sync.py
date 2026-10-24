from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.settings.ofd import OfdSettings
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.fiscal.application.dto import OfdSyncResult
from myasnaya_derevnya.modules.fiscal.application.errors import (
    CashRegisterByRegNumberNotFound,
    InvalidOfdPeriodError,
    OfdApiError,
    OfdNotConfiguredError,
    OfdPeriodBeforeCutoverError,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceipt,
    OfdReceiptLine,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_sync_run import OfdSyncRun
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import RegNumber
from myasnaya_derevnya.modules.fiscal.infrastructure.ofd.client import (
    OfdClient,
    OfdReceiptPayload,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.base import (
    OfdReceiptRepository,
)
from myasnaya_derevnya.modules.fiscal.presentation.fiscal_api import FiscalAPI

logger = logging.getLogger(__name__)

MAX_PERIOD_DAYS = 31


class OfdSyncService:
    """Загружает чеки ОФД в локальное хранилище.

    Сервис не проверяет права: это делает интерактор для HTTP-запроса. CLI
    вызывает сервис напрямую, чтобы синхронизацию можно было запускать из cron.
    """

    def __init__(
        self,
        ofd_client: OfdClient,
        settings: OfdSettings,
        fiscal_api: FiscalAPI,
        catalog_api: CatalogAPI,
        receipt_repository: OfdReceiptRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._ofd_client = ofd_client
        self._settings = settings
        self._fiscal_api = fiscal_api
        self._catalog_api = catalog_api
        self._receipt_repository = receipt_repository
        self._transaction_manager = transaction_manager

    async def sync(
        self,
        *,
        reg_number: str,
        date_from: datetime,
        date_to: datetime,
    ) -> OfdSyncResult:
        normalized = RegNumber.parse(reg_number)
        self._validate_period(date_from, date_to)

        cash_register = await self._fiscal_api.cash_register_by_reg_number(
            normalized.value
        )
        if cash_register is None:
            raise CashRegisterByRegNumberNotFound(normalized.value)

        if not self._settings.ofd_inn:
            raise OfdNotConfiguredError()

        run = OfdSyncRun.start(
            inn=self._settings.ofd_inn,
            reg_number=normalized.value,
            period_from=date_from,
            period_to=date_to,
        )
        await self._receipt_repository.add_sync_run(run)
        await self._transaction_manager.commit()

        # Привязку кассы могли настроить после первой загрузки. Перед новым
        # запросом в ОФД «лечим» чеки, которые ждали склад.
        await self._repair_locations(normalized.value)

        try:
            payloads = await self._ofd_client.fetch_receipts(
                reg_number=normalized.value,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as exc:
            run.fail(str(exc))
            await self._receipt_repository.save_sync_run(run)
            await self._transaction_manager.commit()
            raise

        created = 0
        errors: list[str] = []

        for payload in payloads:
            try:
                receipt = await self._build_receipt(
                    payload=payload,
                    reg_number=normalized.value,
                )
                if await self._receipt_repository.add_if_absent(receipt):
                    created += 1
                    await self._transaction_manager.commit()
                else:
                    await self._transaction_manager.rollback()
            except Exception as exc:  # noqa: BLE001 — один чек не должен ломать пакет
                await self._transaction_manager.rollback()
                errors.append(
                    f"док. {payload.doc_number}: {exc}"
                )
                logger.warning(
                    "Не удалось сохранить чек ОФД",
                    extra={
                        "reg_number": normalized.value,
                        "doc_number": payload.doc_number,
                        "error": str(exc),
                    },
                )

        if errors:
            run.fail("; ".join(errors), found=len(payloads), created=created)
        else:
            run.succeed(found=len(payloads), created=created)

        await self._receipt_repository.save_sync_run(run)
        await self._transaction_manager.commit()

        logger.info(
            "Синхронизация ОФД завершена",
            extra={
                "reg_number": normalized.value,
                "period_from": date_from.isoformat(),
                "period_to": date_to.isoformat(),
                "receipts_found": len(payloads),
                "receipts_created": created,
                "errors": len(errors),
            },
        )

        return OfdSyncResult(
            run_id=run.id,
            status=run.status.value,
            receipts_found=len(payloads),
            receipts_created=created,
            error=run.error,
        )

    async def _repair_locations(self, reg_number: str) -> None:
        receipts = await self._receipt_repository.needs_location_receipts(
            reg_number
        )
        for receipt in receipts:
            try:
                org_unit_id = await self._fiscal_api.cash_register_location_at(
                    reg_number, receipt.doc_datetime
                )
                if org_unit_id is None:
                    continue

                receipt.set_location(org_unit_id)
                await self._receipt_repository.save(receipt)
                await self._transaction_manager.commit()
            except Exception as exc:  # noqa: BLE001 — один чек не должен ломать пакет
                await self._transaction_manager.rollback()
                logger.warning(
                    "Не удалось определить склад для чека ОФД",
                    extra={
                        "receipt_id": str(receipt.id),
                        "reg_number": reg_number,
                        "error": str(exc),
                    },
                )

    async def _build_receipt(
        self,
        *,
        payload: OfdReceiptPayload,
        reg_number: str,
    ) -> OfdReceipt:
        doc_datetime = self._to_utc(payload.doc_datetime_local)
        org_unit_id = await self._fiscal_api.cash_register_location_at(
            reg_number, doc_datetime
        )

        receipt_id = uuid7()
        lines = [
            OfdReceiptLine.create(
                receipt_id=receipt_id,
                line_number=index,
                name=item.name,
                barcode=item.barcode,
                product_code=item.product_code,
                quantity=item.quantity,
                unit=item.unit,
                price_kopecks=item.price_kopecks,
                total_kopecks=item.total_kopecks,
                raw=item.raw,
            )
            for index, item in enumerate(payload.items, start=1)
        ]

        await self._auto_map(lines)

        return OfdReceipt.create(
            receipt_id=receipt_id,
            inn=payload.user_inn or self._settings.ofd_inn,
            reg_number=payload.kkt_reg_number or reg_number,
            fn_number=payload.fn_number,
            doc_number=payload.doc_number,
            fiscal_sign=payload.fiscal_sign,
            raw_id=payload.raw_id or None,
            doc_datetime=doc_datetime,
            c_date_utc=payload.c_date_utc,
            operation_type=payload.operation_type,
            is_correction=payload.is_correction,
            is_bso=payload.is_bso,
            total_kopecks=payload.total_kopecks,
            cash_kopecks=payload.cash_kopecks,
            ecash_kopecks=payload.ecash_kopecks,
            org_unit_id=org_unit_id,
            lines=lines,
            raw=payload.raw,
        )

    async def _auto_map(self, lines: list[OfdReceiptLine]) -> None:
        for line in lines:
            if line.barcode is None:
                continue

            alias = await self._receipt_repository.alias_by_barcode(line.barcode)
            if alias is not None:
                line.map_to(alias.nomenclature_id)
                continue

            nomenclature_id = await self._nomenclature_by_barcode(line.barcode)
            if nomenclature_id is not None:
                line.map_to(nomenclature_id)

    async def _nomenclature_by_barcode(self, barcode: str) -> UUID | None:
        for candidate in self._gtin_candidates(barcode):
            nomenclature_id = await self._catalog_api.nomenclature_id_by_gtin(
                candidate
            )
            if nomenclature_id is not None:
                return nomenclature_id

        return None

    @staticmethod
    def _gtin_candidates(barcode: str) -> list[str]:
        digits = "".join(ch for ch in barcode if ch.isdigit())
        candidates: list[str] = []

        def add(value: str) -> None:
            if value and value not in candidates:
                candidates.append(value)

        add(barcode)
        add(digits)

        if digits.startswith("01") and len(digits) >= 16:
            add(digits[2:16])

        if len(digits) == 13:
            add(digits.zfill(14))

        return candidates

    def _to_utc(self, local: datetime) -> datetime:
        if local.tzinfo is not None:
            return local.astimezone(UTC)

        try:
            timezone = ZoneInfo(self._settings.ofd_timezone)
        except ZoneInfoNotFoundError as exc:
            raise OfdApiError(
                f"неизвестный часовой пояс OFD_TIMEZONE="
                f"{self._settings.ofd_timezone}"
            ) from exc

        return local.replace(tzinfo=timezone).astimezone(UTC)

    def _validate_period(self, date_from: datetime, date_to: datetime) -> None:
        try:
            delta = date_to - date_from
        except TypeError as exc:
            # Нельзя смешивать дату с часовым поясом и без него.
            raise InvalidOfdPeriodError() from exc

        if delta.total_seconds() <= 0:
            raise InvalidOfdPeriodError()

        if delta > timedelta(days=MAX_PERIOD_DAYS):
            raise InvalidOfdPeriodError()

        cutover = self._settings.ofd_cutover_date
        if cutover is not None and date_from.date() < cutover:
            raise OfdPeriodBeforeCutoverError(cutover)
