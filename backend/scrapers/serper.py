"""
Поиск через Serper API (Google Search).
Возвращает сырые результаты, парсеры — отдельно.
"""
import httpx
from config import settings


SERPER_URL = "https://google.serper.dev/search"

GEO_MAP = {
    "egypt": "eg", "morocco": "ma", "algeria": "dz",
    "tunisia": "tn", "libya": "ly", "all": "eg",
}
LANG_MAP = {"en": "en", "ar": "ar", "fr": "fr"}
TYPE_MAP = {"youtube": "videos"}


async def search(query_text: str, source_type: str, geo: str, language: str) -> dict:
    payload = {
        "q": query_text,
        "gl": GEO_MAP.get(geo, "eg"),
        "hl": LANG_MAP.get(language, "en"),
        "num": 10,
    }
    if source_type == "youtube":
        payload["type"] = "videos"

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            SERPER_URL,
            headers={"X-API-KEY": settings.serper_api_key},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
