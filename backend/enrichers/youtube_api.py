"""
YouTube Data API v3 — получаем описание канала и email (если указан).
Бесплатно: 10 000 units/день.
Требует: YOUTUBE_API_KEY в env.
"""
import re
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

_BASE = "https://www.googleapis.com/youtube/v3"
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
_TG_RE = re.compile(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,})")
_WA_RE = re.compile(r"wa\.me/[\d+]+")
_TIMEOUT = 10


def _extract_channel_id(url: str) -> str | None:
    """Extract channel ID or @handle from YouTube URL."""
    patterns = [
        r"youtube\.com/channel/([UC][a-zA-Z0-9_-]{20,})",
        r"youtube\.com/@([a-zA-Z0-9_.-]+)",
        r"youtube\.com/c/([a-zA-Z0-9_.-]+)",
        r"youtube\.com/user/([a-zA-Z0-9_.-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url or "")
        if m:
            return m.group(1)
    return None


async def enrich_channel(channel_id_or_handle: str, url: str = "") -> dict:
    """
    Returns dict with any of: description, contact_email, contact_telegram, contact_other, followers.
    channel_id_or_handle: UC... ID or @handle or custom URL handle
    """
    if not settings.youtube_api_key:
        return {}

    result: dict = {}

    # Determine the right parameter
    cid = channel_id_or_handle or _extract_channel_id(url)
    if not cid:
        return {}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # Try by ID first, then forHandle
            param_key = "id" if cid.startswith("UC") else "forHandle"
            resp = await client.get(
                f"{_BASE}/channels",
                params={
                    "part": "snippet,statistics,brandingSettings",
                    param_key: cid.lstrip("@"),
                    "key": settings.youtube_api_key,
                },
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()

        items = data.get("items", [])
        if not items:
            return {}

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        branding = item.get("brandingSettings", {}).get("channel", {})

        # Description — from brandingSettings (longer) or snippet
        description = branding.get("description") or snippet.get("description") or ""
        if description:
            result["description"] = description[:1000]

        # Subscribers
        subs = stats.get("subscriberCount")
        if subs:
            result["followers"] = int(subs)

        # Parse contacts from description
        if description:
            m = _EMAIL_RE.search(description)
            if m:
                result["contact_email"] = m.group(0)
            m = _TG_RE.search(description)
            if m:
                result["contact_telegram"] = m.group(1)
            m = _WA_RE.search(description)
            if m:
                result["contact_other"] = m.group(0)

        # Country → geo_focus hint
        country = snippet.get("country", "")
        country_map = {"EG": "egypt", "MA": "morocco", "DZ": "algeria", "TN": "tunisia", "LY": "libya"}
        if country in country_map and "geo_focus" not in result:
            result["geo_focus"] = country_map[country]

    except Exception as e:
        logger.debug("YouTube API enrich failed for %s: %s", cid, e)

    return result
