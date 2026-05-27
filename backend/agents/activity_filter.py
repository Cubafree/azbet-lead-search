"""
Фильтр активности: отсекает каналы без постов за последние N дней.
Запускается после базового enrich, ДО дорогого AI-qualify.

Логика:
- Telegram: парсим t.me/s/{handle} — берём datetime последнего поста
- YouTube: upload_date из yt-dlp уже в ch['last_post_at'] (если enrich отработал)
- Не можем определить дату → пропускаем (не фильтруем)
"""
import re
import logging
from datetime import datetime, timezone, timedelta

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}
_TIMEOUT = 8
MAX_INACTIVE_DAYS = 14


def is_recently_active(ch: dict, max_days: int = MAX_INACTIVE_DAYS) -> bool:
    """
    Проверяет поле last_post_at (datetime) уже заполненное enricher-ом.
    Возвращает True если активен или дата неизвестна (benefit of doubt).
    """
    last = ch.get("last_post_at")
    if last is None:
        return True  # неизвестно → не отсекаем
    if isinstance(last, str):
        try:
            last = datetime.fromisoformat(last)
        except ValueError:
            return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    active = last >= cutoff
    if not active:
        logger.debug(
            "Activity filter: skip %s (last post %s)",
            ch.get("handle"), last.date()
        )
    return active


async def fetch_tg_last_post(handle: str) -> datetime | None:
    """
    Загружает t.me/s/{handle} и возвращает дату последнего поста.
    Возвращает None если недоступно или нет постов.
    """
    url = f"https://t.me/s/{handle}"
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, headers=HEADERS, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            html = resp.text
    except Exception as e:
        logger.debug("TG activity fetch failed for %s: %s", handle, e)
        return None

    soup = BeautifulSoup(html, "html.parser")
    times = soup.select("time[datetime]")
    if not times:
        return None

    # Берём максимальную (последнюю) дату из всех <time> на странице
    dates = []
    for t in times:
        raw = t.get("datetime", "")
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dates.append(dt)
        except ValueError:
            pass

    return max(dates) if dates else None


def parse_yt_upload_date(upload_date: str | None) -> datetime | None:
    """
    Конвертирует yt-dlp формат YYYYMMDD → datetime.
    """
    if not upload_date:
        return None
    try:
        return datetime.strptime(str(upload_date), "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
