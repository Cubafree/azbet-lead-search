"""
SEO/Web парсер — для source_type='seo'.
Извлекает аффилиат-сайты из обычных результатов Google.
"""
import re
import httpx
from bs4 import BeautifulSoup


COMPETITORS = ["1xbet", "melbet", "mostbet", "22bet", "1win", "betwinner"]

SKIP_DOMAINS = {
    "askgamblers.com", "casinoguru.com", "trustpilot.com", "tripadvisor.com",
    "google.com", "wikipedia.org", "youtube.com", "facebook.com", "twitter.com",
    "igamingtoday.com", "slotsup.com", "voluum.com", "similarweb.com",
    "gambling.com", "sigma.world", "egr.global", "t.me", "instagram.com",
    "tiktok.com", "linkedin.com",
}

AFFILIATE_SIGNALS = [
    "affiliate disclosure", "affiliate link", "we may earn",
    "advertiser disclosure", "commission", "partner link",
    "btag=", "affid=", "income access", "netrefer",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}


def parse_serper_results(data: dict, language: str, geo: str) -> list[dict]:
    results = data.get("organic", [])
    seen: set[str] = set()
    channels = []

    for item in results:
        url = item.get("link", "")
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        if not m:
            continue
        domain = m.group(1).lower()

        if any(domain.endswith(s) or domain == s for s in SKIP_DOMAINS):
            continue
        if domain in seen:
            continue
        seen.add(domain)

        snippet = item.get("snippet", "")
        title = item.get("title", "")
        full_text = (snippet + " " + title).lower()

        mentioned = [c for c in COMPETITORS if c in full_text]
        has_affiliate_signal = any(s in full_text for s in AFFILIATE_SIGNALS)

        email_m = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", full_text, re.I)

        channels.append({
            "platform": "web",
            "handle": domain,
            "url": url,
            "name": _clean_title(title) or domain.split(".")[0],
            "description": snippet or None,
            "followers": None,
            "mentioned_competitors": ", ".join(mentioned) or None,
            "competitor_promo": None,
            "contact_email": email_m.group(0) if email_m else None,
            "language": language,
            "geo_focus": geo if geo != "all" else None,
            "contact_other": None,
            "_affiliate_signal": has_affiliate_signal,
        })

    return channels


async def enrich_site(url: str) -> dict:
    """Заходит на сайт, ищет email/telegram/WhatsApp в тексте страницы."""
    try:
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {}
            html = resp.text
    except Exception:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    # Убираем скрипты и стили
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)[:3000]  # обрезаем для OpenAI

    email_m = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", text, re.I)
    tg_m = re.search(r"(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{3,})", text)
    wa_m = re.search(r"(?:wa\.me|whatsapp\.com/send\?phone=)(\d{7,15})", text)

    return {
        "contact_email": email_m.group(0) if email_m else None,
        "contact_telegram": tg_m.group(1) if tg_m else None,
        "contact_other": f"https://wa.me/{wa_m.group(1)}" if wa_m else None,
        "_page_text": text,  # передадим в AI для анализа
    }


def _clean_title(title: str) -> str:
    title = re.sub(r"\s*[-|]\s*\d{4}.*$", "", title)
    return title.strip()
