"""
TikTok account parser — extracts handles from Serper organic results.
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

COMPETITORS = ["1xbet", "melbet", "mostbet", "22bet", "1win", "betwinner"]

_FOLLOWERS_RE = re.compile(
    r"([\d,.]+)\s*[Kk]\s*[Ff]ollowers|"
    r"([\d,.]+)\s*[Mm]\s*[Ff]ollowers|"
    r"([\d,]+)\s+[Ff]ollowers|"
    r"([\d,.]+)\s*[Kk]\s*[Ll]ikes",
    re.IGNORECASE,
)


def _extract_handle(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        if "tiktok.com" not in parsed.netloc:
            return None
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return None
        first = parts[0]
        # TikTok handles start with @
        if first.startswith("@"):
            username = first[1:]
            if re.fullmatch(r"[A-Za-z0-9._]{1,24}", username):
                return username
        return None
    except Exception:
        return None


def _parse_followers(text: str) -> int | None:
    if not text:
        return None
    m = _FOLLOWERS_RE.search(text)
    if not m:
        return None
    raw = next((g for g in m.groups() if g), None)
    if not raw:
        return None
    raw = raw.replace(",", "").replace(".", "").strip()
    try:
        value = int(raw)
        group0 = m.group(0).upper()
        if "M" in group0:
            value *= 1_000_000
        elif "K" in group0:
            value *= 1_000
        return value
    except ValueError:
        return None


def parse_serper_results(data: dict, language: str, geo: str) -> list[dict]:
    results = data.get("organic", [])
    channels: list[dict] = []
    seen: set[str] = set()

    for item in results:
        url: str = item.get("link", "")
        if "tiktok.com" not in url:
            continue
        handle = _extract_handle(url)
        if not handle or handle in seen:
            continue
        seen.add(handle)

        title: str = item.get("title", "")
        snippet: str = item.get("snippet", "")
        full_text = (snippet + " " + title).lower()
        followers = _parse_followers(snippet) or _parse_followers(title)
        mentioned = [c for c in COMPETITORS if c in full_text]
        promo_m = re.search(
            r"(?:promo\s*code|code|كود|بروموكود)[:\s]+([A-Z0-9]{3,15})", full_text, re.I
        )

        channels.append({
            "platform": "tiktok",
            "handle": handle,
            "url": f"https://www.tiktok.com/@{handle}",
            "name": title.split("|")[0].split("(")[0].strip() or handle,
            "description": snippet or None,
            "followers": followers,
            "mentioned_competitors": ", ".join(mentioned) or None,
            "competitor_promo": promo_m.group(1) if promo_m else None,
            "language": language,
            "geo_focus": geo if geo != "all" else None,
            "contact_email": None,
        })

    return channels
