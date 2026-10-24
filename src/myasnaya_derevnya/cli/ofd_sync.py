import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta

from starlette.requests import Request

from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.modules.fiscal.application.services.ofd_sync import (
    OfdSyncService,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Загрузить чеки ОФД за период в локальное хранилище."
    )
    parser.add_argument("--reg-number", required=True, help="РНМ кассы, 16 цифр")
    parser.add_argument(
        "--date-from",
        type=datetime.fromisoformat,
        help="Начало периода, ISO (например 2026-10-24T00:00:00)",
    )
    parser.add_argument(
        "--date-to",
        type=datetime.fromisoformat,
        help="Конец периода, ISO",
    )
    parser.add_argument(
        "--last-hours",
        type=int,
        help="Загрузить чеки за последние N часов (вместо --date-from/--date-to)",
    )
    return parser.parse_args()


def _period(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.last_hours is not None:
        if args.last_hours <= 0:
            raise SystemExit("--last-hours должен быть больше нуля")
        date_to = datetime.now().replace(microsecond=0)
        return date_to - timedelta(hours=args.last_hours), date_to

    if args.date_from is None or args.date_to is None:
        raise SystemExit(
            "Укажите --date-from и --date-to либо --last-hours"
        )

    return args.date_from, args.date_to


async def _run(
    *, reg_number: str, date_from: datetime, date_to: datetime
) -> dict:
    request = Request(
        {
            "type": "http",
            "method": "CLI",
            "path": "/cli/ofd-sync",
            "headers": [],
        }
    )

    async with container(context={Request: request}) as context:
        service = await context.get(OfdSyncService)
        result = await service.sync(
            reg_number=reg_number,
            date_from=date_from,
            date_to=date_to,
        )

    return {
        "run_id": str(result.run_id),
        "status": result.status,
        "receipts_found": result.receipts_found,
        "receipts_created": result.receipts_created,
        "error": result.error,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    date_from, date_to = _period(args)

    try:
        result = asyncio.run(
            _run(
                reg_number=args.reg_number,
                date_from=date_from,
                date_to=date_to,
            )
        )
    except Exception as exc:
        logging.getLogger(__name__).error("Синхронизация ОФД не выполнена: %s", exc)
        raise SystemExit(1) from exc

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
