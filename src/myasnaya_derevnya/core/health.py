from fastapi import APIRouter, Response
from sqlalchemy import text

from myasnaya_derevnya.core.database.connection import async_session_maker

router = APIRouter(tags=["Служебные"])


@router.get("/health", description="Живой ли процесс")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", description="Готов ли принимать запросы (проверка БД)")
async def ready(response: Response) -> dict[str, str]:
    try:
        async with async_session_maker() as session:
            await session.execute(text("select 1"))
    except Exception:  # noqa: BLE001 — наружу отдаём только статус
        response.status_code = 503
        return {"status": "unavailable"}

    return {"status": "ok"}
