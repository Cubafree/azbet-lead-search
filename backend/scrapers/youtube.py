"""
YouTube-парсер.
1. parse_serper_results — извлекает каналы из видео-результатов Serper
2. enrich_channel      — yt-dlp достаёт полные метаданные канала
"""
import re
import asyncio
from yt_dlp import YoutubeDL


COMPETITORS = ["1xbet", "melbet", "mostbet", "22bet", "1win", "betwinner"]


def parse_serper_results(data: dict, language: str, geo: str) -> list[dict]:
    """Группирует видеорезультаты по каналу."""
    results = data.get("videos", [])
    by_channel: dict[str, dict] = {}

    for item in results:
        channel = item.get("channel")
        if not channel:
            continue
        if channel not in by_channel:
            by_channel[channel] = {"titles": [], "snippets": [], "links": []}
        by_channel[channel]["titles"].append(item.get("title", ""))
        by_channel[channel]["snippets"].append(item.get("snippet", ""))
        by_channel[channel]["links"].append(item.get("link", ""))

    channels = []
    for channel_name, d in by_channel.items():
        full_text = " ".join(d["snippets"] + d["titles"]).lower()
        mentioned = [c for c in COMPETITORS if c in full_text]

        # handle = slug из имени канала
        handle = "yt_" + re.sub(r"[^a-z0-9]", "_", channel_name.lower()).strip("_")

        channels.append({
            "platform": "youtube",
            "handle": handle,
            "url": d["links"][0] if d["links"] else None,  # ссылка на видео (обогатим потом)
            "name": channel_name,
            "description": d["snippets"][0] if d["snippets"] else None,
            "followers": None,  # заполним при enrich
            "mentioned_competitors": ", ".join(mentioned) or None,
            "competitor_promo": None,
            "language": language,
            "geo_focus": geo if geo != "all" else None,
            "contact_email": None,
        })

    return channels


async def enrich_channel(video_url: str) -> dict:
    """
    Берёт ссылку на любое видео канала, достаёт метаданные самого канала через yt-dlp.
    Возвращает: channel_url, name, subscribers, description, contact_email, channel_id.
    """
    if not video_url:
        return {}

    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "no_warnings": True,
    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _extract(video_url, opts))
    except Exception:
        return {}

    if not info:
        return {}

    # Email из описания канала
    description = info.get("channel_description") or info.get("description") or ""
    email_m = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", description, re.I)

    # Подписчики
    followers = info.get("channel_follower_count") or info.get("uploader_follower_count")

    channel_url = info.get("channel_url") or info.get("uploader_url")

    return {
        "url": channel_url,
        "name": info.get("channel") or info.get("uploader"),
        "followers": followers,
        "description": description[:500] if description else None,
        "contact_email": email_m.group(0) if email_m else None,
    }


def _extract(url: str, opts: dict) -> dict | None:
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)
