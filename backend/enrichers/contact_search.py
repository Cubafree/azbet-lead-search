"""
Кросс-поиск контактов через Serper.
Ищет email/TG/сайт по имени канала если прямые методы не дали результата.
"""
import re
import logging
from scrapers.serper import search as serper_search

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}")
_TG_RE = re.compile(r"(?:t\.me/|@)([a-zA-Z0-9_]{4,})")
_WA_RE = re.compile(r"wa\.me/[\d+]+")

# Домены которые не являются контактами
_SKIP_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "example.com", "domain.com"}


def _clean_email(email: str) -> str | None:
    domain = email.split("@")[-1].lower()
    if domain in _SKIP_DOMAINS or email.endswith(".png") or email.endswith(".jpg"):
        return None
    return email


async def find_contacts(channel: dict) -> dict:
    """
    Uses Serper to search for contact info for a channel that has none.
    Returns dict with any of: contact_email, contact_telegram, contact_other.
    """
    name = channel.get("name") or channel.get("handle") or ""
    platform = channel.get("platform") or ""
    if not name:
        return {}

    result: dict = {}

    queries = [
        f'"{name}" contact email',
        f'"{name}" telegram OR whatsapp',
    ]
    if platform == "youtube":
        queries.insert(0, f'"{name}" site:youtube.com email')

    for query in queries:
        try:
            data = await serper_search(query, "seo", "all", "en")
            snippets = []
            for item in data.get("organic", []):
                snippets.append(item.get("snippet", ""))
                snippets.append(item.get("title", ""))
            text = " ".join(snippets)

            if not result.get("contact_email"):
                m = _EMAIL_RE.search(text)
                if m:
                    cleaned = _clean_email(m.group(0))
                    if cleaned:
                        result["contact_email"] = cleaned

            if not result.get("contact_telegram"):
                m = _TG_RE.search(text)
                if m and m.group(1).lower() not in (name.lower(), "joinchat"):
                    result["contact_telegram"] = m.group(1)

            if not result.get("contact_other"):
                m = _WA_RE.search(text)
                if m:
                    result["contact_other"] = m.group(0)

            # Stop early if we found something useful
            if result.get("contact_email") or result.get("contact_telegram"):
                break

        except Exception as e:
            logger.debug("Contact search failed for '%s': %s", name, e)

    return result
