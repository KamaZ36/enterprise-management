from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from myasnaya_derevnya.core.settings.ofd import OfdSettings
from myasnaya_derevnya.modules.fiscal.application.errors import (
    OfdApiError,
    OfdNotConfiguredError,
)


@dataclass(frozen=True, slots=True)
class OfdReceiptItemPayload:
    name: str
    price_kopecks: int
    quantity: Decimal
    total_kopecks: int
    barcode: str | None
    product_code: dict
    unit: str | None
    raw: dict


@dataclass(frozen=True, slots=True)
class OfdReceiptPayload:
    raw_id: str
    c_date_utc: datetime | None
    doc_datetime_local: datetime
    operation_type: str
    is_bso: bool
    is_correction: bool
    user_inn: str
    kkt_reg_number: str
    fn_number: str
    doc_number: int
    fiscal_sign: str
    total_kopecks: int
    cash_kopecks: int
    ecash_kopecks: int
    items: tuple[OfdReceiptItemPayload, ...]
    raw: dict


class OfdClient:
    """Клиент интеграционного API ОФД.

    Используется только ``receipts-with-fpd-short``: в нём есть штрихкод
    товара, по которому можно автоматически сопоставить номенклатуру.
    """

    MIN_INTERVAL_SECONDS = 1.05

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        settings: OfdSettings,
    ) -> None:
        self._http_client = http_client
        self._settings = settings
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def fetch_receipts(
        self,
        *,
        reg_number: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[OfdReceiptPayload]:
        if not self._settings.ofd_api_token or not self._settings.ofd_inn:
            raise OfdNotConfiguredError()

        url = (
            f"{self._settings.ofd_api_url.rstrip('/')}/inn/"
            f"{self._settings.ofd_inn}/kkt/{reg_number}/receipts-with-fpd-short"
        )
        data = await self._get(
            url,
            params={
                "dateFrom": self._local_naive(date_from).isoformat(
                    timespec="seconds"
                ),
                "dateTo": self._local_naive(date_to).isoformat(timespec="seconds"),
                "AuthToken": self._settings.ofd_api_token,
            },
        )

        if data.get("Status") != "Success":
            raise OfdApiError(self._errors_text(data))

        return [self._parse_receipt(item) for item in data.get("Data") or []]

    async def _get(self, url: str, *, params: dict) -> dict:
        async with self._lock:
            wait_for = self.MIN_INTERVAL_SECONDS - (
                time.monotonic() - self._last_request_at
            )
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_request_at = time.monotonic()

        try:
            response = await self._http_client.get(
                url,
                params=params,
                timeout=self._settings.ofd_request_timeout,
            )
        except httpx.HTTPError as exc:
            raise OfdApiError(f"не удалось выполнить запрос ({exc})") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise OfdApiError(
                f"ответ не является JSON (HTTP {response.status_code})"
            ) from exc

        if response.status_code >= 400 or data.get("Status") != "Success":
            raise OfdApiError(self._errors_text(data))

        return data

    @staticmethod
    def _errors_text(data: dict) -> str:
        errors = data.get("Errors")
        if isinstance(errors, list):
            parts: list[str] = []
            for error in errors:
                if isinstance(error, dict):
                    parts.append(
                        str(error.get("Message") or error.get("Code") or error)
                    )
                else:
                    parts.append(str(error))
            if parts:
                return "; ".join(parts)

        if isinstance(errors, str) and errors:
            return errors

        return "неизвестная ошибка интеграции"

    @classmethod
    def _parse_receipt(cls, raw: dict) -> OfdReceiptPayload:
        doc_datetime_raw = raw.get("DocDateTime")
        if not doc_datetime_raw:
            raise OfdApiError("в чеке нет даты документа")

        doc_number_raw = raw.get("DocNumber")
        if doc_number_raw is None:
            raise OfdApiError("в чеке нет номера документа")

        fiscal_sign = str(
            raw.get("DecimalFiscalSign") or raw.get("FiscalSign") or ""
        ).strip()
        raw_id = str(raw.get("Id") or raw.get("DocRawId") or "").strip()
        if not fiscal_sign:
            # Фискальный признак — часть ключа идемпотентности. Без него
            # чек нельзя безопасно перепроводить.
            raise OfdApiError("в чеке нет фискального признака")

        items = tuple(
            cls._parse_item(item) for item in raw.get("Items") or []
        )

        return OfdReceiptPayload(
            raw_id=raw_id,
            c_date_utc=cls._parse_utc(raw.get("CDateUtc")),
            doc_datetime_local=cls._parse_local(doc_datetime_raw),
            operation_type=str(raw.get("OperationType") or ""),
            is_bso=bool(raw.get("IsBso")),
            is_correction=bool(raw.get("IsCorrection")),
            user_inn=str(raw.get("UserInn") or ""),
            kkt_reg_number=str(raw.get("KktRegNumber") or ""),
            fn_number=str(raw.get("FnNumber") or ""),
            doc_number=int(doc_number_raw),
            fiscal_sign=fiscal_sign,
            total_kopecks=int(raw.get("TotalSumm") or 0),
            cash_kopecks=int(raw.get("CashSumm") or 0),
            ecash_kopecks=int(raw.get("ECashSumm") or 0),
            items=items,
            raw=raw,
        )

    @classmethod
    def _parse_item(cls, raw: dict) -> OfdReceiptItemPayload:
        try:
            quantity = Decimal(str(raw.get("Quantity", "0")).replace(",", "."))
        except InvalidOperation as exc:
            raise OfdApiError(
                f"некорректное количество в строке «{raw.get('Name')}»"
            ) from exc

        unit = raw.get("ProductUnitOfMeasure")
        return OfdReceiptItemPayload(
            name=str(raw.get("Name") or "").strip(),
            price_kopecks=int(raw.get("Price") or 0),
            quantity=quantity,
            total_kopecks=int(raw.get("Total") or 0),
            barcode=raw.get("Barcode"),
            product_code=raw.get("ProductCode") or {},
            unit=str(unit) if unit is not None else None,
            raw=raw,
        )

    @staticmethod
    def _parse_local(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise OfdApiError(f"некорректная дата документа: {value}") from exc

    def _local_naive(self, value: datetime) -> datetime:
        """ОФД принимает границы периода без часового пояса.

        Время трактуем в часовом поясе кассы: так его видит оператор в чеке.
        """

        if value.tzinfo is None:
            return value

        try:
            timezone = ZoneInfo(self._settings.ofd_timezone)
        except ZoneInfoNotFoundError as exc:
            raise OfdApiError(
                "неизвестный часовой пояс OFD_TIMEZONE="
                f"{self._settings.ofd_timezone}"
            ) from exc

        return value.astimezone(timezone).replace(tzinfo=None)

    @staticmethod
    def _parse_utc(value: str | None) -> datetime | None:
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise OfdApiError(f"некорректная дата приёма: {value}") from exc

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
