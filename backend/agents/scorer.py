"""
Numeric lead score 0-100 replacing the loose high/medium/low bucketing.
Called after AI qualify; result stored in channels.score column.
"""
from datetime import datetime, timezone

_FOLLOWER_TIERS = [
    (1_000_000, 30),
    (500_000,   25),
    (100_000,   20),
    (50_000,    15),
    (10_000,    10),
    (1_000,      5),
]


def _follower_score(followers: int | None) -> int:
    if not followers:
        return 0
    for threshold, points in _FOLLOWER_TIERS:
        if followers >= threshold:
            return points
    return 2


def _recency_score(last_post_at) -> int:
    """Up to 20 pts — penalise stale channels."""
    if not last_post_at:
        return 5   # unknown → neutral
    try:
        if isinstance(last_post_at, str):
            last_post_at = datetime.fromisoformat(last_post_at)
        if last_post_at.tzinfo is None:
            last_post_at = last_post_at.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - last_post_at).days
        if days <= 3:
            return 20
        if days <= 7:
            return 15
        if days <= 14:
            return 10
        if days <= 30:
            return 5
        return 0
    except Exception:
        return 5


def score_channel(ch: dict) -> int:
    """
    Returns integer score 0-100 for a channel dict.
    Breakdown (max points):
      followers  : 30
      recency    : 20
      contacts   : 20  (email=15, tg=10, other=5)
      priority   : 15  (high=15, medium=10, low=3)
      geo_match  : 10  (explicit MENA geo set)
      competitor : 5   (promotes competitors — confirms niche)
    """
    score = 0

    # Followers (30)
    score += _follower_score(ch.get("followers"))

    # Recency (20)
    score += _recency_score(ch.get("last_post_at"))

    # Contacts (20) — up to 20 but capped
    contact_pts = 0
    if ch.get("contact_email"):
        contact_pts += 15
    if ch.get("contact_telegram"):
        contact_pts += 10
    if ch.get("contact_other"):
        contact_pts += 5
    score += min(contact_pts, 20)

    # AI priority (15)
    priority_pts = {"high": 15, "medium": 10, "low": 3}.get(
        (ch.get("priority") or "").lower(), 0
    )
    score += priority_pts

    # Geo match (10)
    _MENA = {"egypt", "morocco", "algeria", "tunisia", "libya", "mena", "arab", "maghreb"}
    geo = (ch.get("geo_focus") or "").lower().strip()
    if geo in _MENA:
        score += 10

    # Competitor signal (5) — promotes competitors = confirmed niche
    if ch.get("mentioned_competitors") or ch.get("competitor_promo"):
        score += 5

    return min(score, 100)


def priority_from_score(score: int) -> str:
    """Derive the legacy priority bucket from numeric score."""
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"
