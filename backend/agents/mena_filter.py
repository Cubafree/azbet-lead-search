"""
Быстрый text-based MENA pre-filter — запускается ДО дорогого AI-qualify.
Отсекает каналы, явно не связанные с MENA регионом.
"""
import re

_ARABIC_RE = re.compile(r"[؀-ۿ]")

_MENA_KEYWORDS = {
    "egypt", "مصر", "egyptian",
    "morocco", "المغرب", "maroc", "moroccan",
    "algeria", "الجزائر", "algérie", "algerie", "algerian",
    "tunisia", "تونس", "tunisie", "tunisian",
    "libya", "ليبيا", "libyan",
    "mena", "arab", "عربي", "عرب", "arabic",
    "maghreb", "المغرب العربي", "شمال افريقيا",
}

_NON_MENA_PATTERNS = [
    r"\buk\s+betting\b", r"\bpremier\s+league\s+only\b",
    r"русские\s+ставки", r"\brussia\b", r"\bинди[яи]\b",
    r"\bindia\b", r"\bindian\s+betting\b",
    r"\bnigeria\s+only\b", r"\busa\s+only\b",
    r"\bchina\b", r"\bjapanese\b", r"\bkorean\s+betting\b",
]
_NON_MENA_RE = re.compile("|".join(_NON_MENA_PATTERNS), re.IGNORECASE)

_MENA_GEO_VALUES = {"egypt", "morocco", "algeria", "tunisia", "libya", "mena", "arab", "maghreb"}
_SOCIAL_PLATFORMS = {"telegram", "youtube"}
_LARGE_THRESHOLD = 5_000


def _blob(channel: dict) -> str:
    return " ".join(filter(None, [
        channel.get("description") or "",
        channel.get("name") or "",
        channel.get("handle") or "",
        channel.get("language") or "",
        channel.get("geo_focus") or "",
    ]))


def is_mena_relevant(channel: dict) -> bool:
    """
    Return True if channel may be relevant for MENA affiliate outreach.
    Conservative: only reject if there is strong non-MENA evidence.
    """
    # geo_focus already set to MENA value → immediate pass
    geo_focus = (channel.get("geo_focus") or "").lower().strip()
    if geo_focus in _MENA_GEO_VALUES:
        return True

    description = channel.get("description")

    # No description → can't judge, let AI decide
    if not description:
        return True

    blob = _blob(channel)

    # Arabic script → pass
    if _ARABIC_RE.search(blob):
        return True

    blob_lower = blob.lower()

    # MENA keyword match → pass
    for kw in _MENA_KEYWORDS:
        if kw.lower() in blob_lower:
            return True

    # Large social channel → benefit of the doubt
    platform = (channel.get("platform") or "").lower()
    followers = channel.get("followers") or 0
    if platform in _SOCIAL_PLATFORMS and followers >= _LARGE_THRESHOLD:
        return True

    # Explicit non-MENA signal with no positive evidence → reject
    if _NON_MENA_RE.search(blob):
        return False

    # Default: pass (AI qualify will decide)
    return True
