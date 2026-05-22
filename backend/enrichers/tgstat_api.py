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

        if item.get("subscribers_count"):
            result["followers"] = item["subscribers_count"]
        if item.get("description"):
            result["description"] = item["description"][:1000]

        # TGStat sometimes exposes contact info for verified channels
        contact = item.get("contact_info") or {}
        if contact.get("email"):
            result["contact_email"] = contact["email"]
        if contact.get("phone"):
            result["contact_other"] = contact["phone"]

        # username of linked account/admin
        if item.get("username") and item["username"].lower() != handle.lower():
            result["contact_telegram"] = item["username"]

    except Exception as e:
        logger.debug("TGStat enrich failed for %s: %s", handle, e)

    return result
