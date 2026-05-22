"""
TGStat API — статистика и контакты Telegram-каналов.
https://tgstat.ru/developers  (бесплатно: 1000 req/день)
Требует: TGSTAT_TOKEN в env.
"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.tgstat.ru"
_TIMEOUT = 10


async def enrich_channel(handle: str) -> dict:
    """
    Returns dict with any of: followers, description, contact_email, contact_telegram, contact_other.
    handle: Telegram @username without @
    """
    if not settings.tgstat_token:
        return {}

    result: dict = {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{_BASE}/channels/get",
                params={"token": settings.tgstat_token, "channelId": f"@{handle}"},
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()

        if data.get("status") != "ok":
            return {}

        item = data.get("response", {})

        # Correct field names per TGStat API docs
        if item.get("participants_count"):
            result["followers"] = item["participants_count"]
        if item.get("about"):
            result["description"] = item["about"][:1000]

        # username — strip leading @ if present
        username = (item.get("username") or "").lstrip("@")
        if username and username.lower() != handle.lower():
            result["contact_telegram"] = username

    except Exception as e:
        logger.debug("TGStat enrich failed for %s: %s", handle, e)

    return result
