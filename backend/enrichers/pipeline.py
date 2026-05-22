"""
Общий пайплайн глубокого обогащения.
Используется и в job_runner (inline для high/medium) и в api/enrich (ручной батч).
"""
import logging
from enrichers import telegram_deep, tgstat_api, youtube_api, contact_search
from scrapers import serper, telegram as tg_scraper, youtube as yt_scraper, web as web_scraper

logger = logging.getLogger(__name__)


async def deep_enrich(ch: dict) -> dict:
    """
    Запускает все доступные enricher-ы для канала.
    Возвращает merged dict с найденными данными.
    """
    platform = ch.get("platform", "")
    handle = ch.get("handle", "")
    url = ch.get("url", "")
    result: dict = {}

    if platform == "telegram":
        # 1. Telethon — admins, last messages, linked group
        r = await telegram_deep.enrich_channel(handle)
        result.update({k: v for k, v in r.items() if v})

        # 2. TGStat — participants_count, about
        if not result.get("contact_email"):
            r = await tgstat_api.enrich_channel(handle)
            result.update({k: v for k, v in r.items() if v and k not in result})

    elif platform == "youtube":
        r = await youtube_api.enrich_channel(handle, url)
        result.update({k: v for k, v in r.items() if v})

    # Cross-search через Serper для любой платформы без контакта
    has_contact = result.get("contact_email") or result.get("contact_telegram") or result.get("contact_other")
    existing_contact = ch.get("contact_email") or ch.get("contact_telegram") or ch.get("contact_other")
    if not has_contact and not existing_contact:
        r = await contact_search.find_contacts(ch)
        result.update({k: v for k, v in r.items() if v})

    return result


async def discover_cross_platform(ch: dict, geo: str = "all") -> list[dict]:
    """
    Ищет того же аффилиата на других платформах.
    TG-канал → ищем их YouTube + сайт.
    YouTube-канал → ищем их TG.
    Возвращает список найденных каналов для последующего сохранения.
    """
    name = ch.get("name") or ch.get("handle") or ""
    platform = ch.get("platform", "")
    if not name or len(name) < 4:
        return []

    discovered: list[dict] = []

    try:
        if platform == "telegram":
            # Ищем их YouTube
            yt_data = await serper.search(f'"{name}" youtube.com/@', "youtube", geo, "en")
            yt_channels = yt_scraper.parse_serper_results(yt_data, "en", geo)
            for c in yt_channels[:2]:   # max 2 результата
                c["_discovered_from"] = ch.get("handle")
                discovered.append(c)

            # Ищем их сайт
            web_data = await serper.search(f'"{name}" betting tips site', "seo", geo, "en")
            web_sites = web_scraper.parse_serper_results(web_data, "en", geo)
            for c in web_sites[:1]:     # max 1 сайт
                c["_discovered_from"] = ch.get("handle")
                discovered.append(c)

        elif platform == "youtube":
            # Ищем их Telegram
            tg_data = await serper.search(f'"{name}" site:t.me', "telegram", geo, "en")
            tg_channels = tg_scraper.parse_serper_results(tg_data, "en", geo)
            for c in tg_channels[:2]:
                c["_discovered_from"] = ch.get("handle")
                discovered.append(c)

        elif platform == "web":
            # Ищем их TG
            tg_data = await serper.search(f'"{name}" site:t.me', "telegram", geo, "en")
            tg_channels = tg_scraper.parse_serper_results(tg_data, "en", geo)
            for c in tg_channels[:1]:
                c["_discovered_from"] = ch.get("handle")
                discovered.append(c)

    except Exception as e:
        logger.debug("Cross-platform discovery failed for %s: %s", name, e)

    return discovered
