"""
Парсинг Telegram-каналов.
1. parse_serper_results — извлекает хендлы из результатов Serper
2. enrich_channel     — загружает t.me страницу и достаёт метаданные
"""
import re
import httpx
from bs4 import BeautifulSoup


COMPETITORS = ["1xbet", "melbet", "mostbet", "22bet", "1win", "betwinner"]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}


def parse_serper_results(data: dict, language: str, geo: str) -> list[dict]:
    results = data.get("organic", [])
    by_username: dict[str, dict] = {}

    for item in results:
        url = item.get("link", "")
        m = re.search(r"t\.me/(?:s/)?([a-zA-Z0-9_]+)", url)
        if not m:
            continue
        username = m.group(1).lower()
        if username in ("joinchat", "share", "iv"):
            continue

        if username not in by_username:
            by_username[username] = {
                "titles": [],
                "snippets": [],
            }
        by_username[username]["titles"].append(item.get("title", ""))
        by_username[username]["snippets"].append(item.get("snippet", ""))

    channels = []
    for username, d in by_username.items():
        full_text = " ".join(d["snippets"] + d["titles"]).lower()

        # Подписчики из сниппета
        sub_match = re.search(
            r"([\d][\d\s]{2,})\s*(?:subscribers|подписчик|مشترك)", full_text, re.I
        )
        followers = None
        if sub_match:
            raw = sub_match.group(1).replace(" ", "")
            followers = int(raw) if raw.isdigit() else None

        # Конкуренты
        mentioned = [c for c in COMPETITORS if c in full_text]

        # Промокод
        promo_m = re.search(
            r"(?:promo\s*code|code|كود|بروموكود)[:\s]+([A-Z0-9]{3,15})", full_text, re.I
        )

        channels.append({
            "platform": "telegram",
            "handle": username,
            "url": f"https://t.me/{username}",
            "name": _clean_title(d["titles"][0]) if d["titles"] else username,
            "description": d["snippets"][0] if d["snippets"] else None,
            "followers": followers,
            "mentioned_competitors": ", ".join(mentioned) or None,
            "competitor_promo": promo_m.group(1) if promo_m else None,
            "language": language,
            "geo_focus": geo if geo != "all" else None,
        })

    return channels


async def enrich_channel(handle: str) -> dict:
    """Загружает t.me/<handle> и извлекает актуальные данные."""
    url = f"https://t.me/{handle}"
    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {}
            html = resp.text
    except Exception:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    # Название
    name_tag = soup.select_one(".tgme_page_title span")
    name = name_tag.get_text(strip=True) if name_tag else None

    # Описание
    desc_tag = soup.select_one(".tgme_page_description")
    description = desc_tag.get_text(strip=True) if desc_tag else None

    # Подписчики
    extra_tag = soup.select_one(".tgme_page_extra")
    followers = None
    if extra_tag:
        m = re.search(r"([\d\s]+)\s*subscribers", extra_tag.get_text(), re.I)
        if m:
            followers = int(m.group(1).replace(" ", "").replace("\xa0", "")) or None

    # Контакт — @username в описании
    contact_telegram = None
    if description:
        cm = re.search(r"@([a-zA-Z0-9_]{3,})", description)
        if cm and cm.group(1).lower() != handle.lower():
            contact_telegram = cm.group(1)

    # Email в описании
    contact_email = None
    if description:
        em = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", description, re.I)
        if em:
            contact_email = em.group(0)

    return {
        "name": name,
        "description": description,
        "followers": followers,
        "contact_telegram": contact_telegram,
        "contact_email": contact_email,
    }


def _clean_title(title: str) -> str:
    title = re.sub(r"\s*[–-]\s*Telegram\s*", "", title, flags=re.I)
    title = re.sub(r"Telegram:\s*View\s*@\w+", "", title, flags=re.I)
    return title.strip()
