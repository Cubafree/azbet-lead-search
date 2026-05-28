import re
from fastapi import APIRouter, Query
from db.pool import get_pool

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("")
async def list_channels(
    platform: str | None = Query(None),
    priority: str | None = Query(None),
    geo_focus: str | None = Query(None),
    niche: str | None = Query(None),
    search: str | None = Query(None),
    show_archived: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    pool = await get_pool()

    conditions = ["1=1"]
    params: list = []
    p = 1

    # По умолчанию скрываем архивные
    if not show_archived:
        conditions.append("is_archived = FALSE")

    if platform:
        conditions.append(f"platform = ${p}")
        params.append(platform)
        p += 1
    if priority:
        conditions.append(f"priority = ${p}")
        params.append(priority)
        p += 1
    if geo_focus:
        conditions.append(f"geo_focus ILIKE ${p}")
        params.append(f"%{geo_focus}%")
        p += 1
    if niche:
        conditions.append(f"niche = ${p}")
        params.append(niche)
        p += 1
    if search:
        conditions.append(f"(name ILIKE ${p} OR handle ILIKE ${p} OR description ILIKE ${p})")
        params.append(f"%{search}%")
        p += 1

    where = " AND ".join(conditions)

    rows = await pool.fetch(
        f"""
        SELECT * FROM channels
        WHERE {where}
        ORDER BY
            CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            created_at DESC
        LIMIT ${p} OFFSET ${p+1}
        """,
        *params, limit, offset,
    )

    total = await pool.fetchval(f"SELECT COUNT(*) FROM channels WHERE {where}", *params)

    return {"total": total, "items": [dict(r) for r in rows]}


@router.patch("/{channel_id}")
async def update_channel(channel_id: str, body: dict):
    pool = await get_pool()
    allowed = {
        "priority", "niche", "geo_focus",
        "contact_email", "contact_telegram", "contact_other",
        "affiliate_id", "is_archived", "is_contacted",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return {"ok": False, "error": "no valid fields"}

    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    await pool.execute(
        f"UPDATE channels SET {sets} WHERE id = $1",
        channel_id, *updates.values(),
    )
    return {"ok": True}


@router.post("/{channel_id}/archive")
async def archive_channel(channel_id: str):
    pool = await get_pool()
    await pool.execute("UPDATE channels SET is_archived = TRUE WHERE id = $1", channel_id)
    return {"ok": True}


@router.post("/{channel_id}/unarchive")
async def unarchive_channel(channel_id: str):
    pool = await get_pool()
    await pool.execute("UPDATE channels SET is_archived = FALSE WHERE id = $1", channel_id)
    return {"ok": True}


@router.get("/stats")
async def stats():
    pool = await get_pool()
    total = await pool.fetchval("SELECT COUNT(*) FROM channels WHERE is_archived = FALSE")
    archived = await pool.fetchval("SELECT COUNT(*) FROM channels WHERE is_archived = TRUE")
    avg_score = await pool.fetchval(
        "SELECT ROUND(AVG(score)) FROM channels WHERE is_archived = FALSE AND score IS NOT NULL"
    )
    by_platform = await pool.fetch(
        "SELECT platform, COUNT(*) as cnt FROM channels WHERE is_archived = FALSE "
        "GROUP BY platform ORDER BY cnt DESC"
    )
    by_priority = await pool.fetch(
        "SELECT priority, COUNT(*) as cnt FROM channels WHERE is_archived = FALSE "
        "GROUP BY priority"
    )
    return {
        "total": total,
        "archived": archived,
        "avg_score": int(avg_score) if avg_score else None,
        "by_platform": [dict(r) for r in by_platform],
        "by_priority": [dict(r) for r in by_priority],
    }


@router.post("/group-affiliates")
async def group_affiliates():
    """
    Group channels by likely affiliate entity using name similarity.
    Channels sharing the same name root (first significant word) get linked
    to the same affiliate record (creates affiliates row if needed).
    Returns count of groupings made.
    """
    pool = await get_pool()

    # Fetch all non-archived channels without an affiliate_id
    rows = await pool.fetch(
        "SELECT id, name, handle, platform FROM channels "
        "WHERE is_archived = FALSE AND affiliate_id IS NULL AND name IS NOT NULL"
    )

    def _key(name: str) -> str:
        """Normalised key: first two meaningful words, lowercased, no punctuation."""
        words = re.sub(r"[^\w\s]", "", name.lower()).split()
        stop = {"the", "a", "an", "of", "de", "le", "la", "el", "al", "tips",
                "bet", "sport", "channel", "official", "page"}
        meaningful = [w for w in words if w not in stop and len(w) > 2]
        return " ".join(meaningful[:2]) if meaningful else name.lower()[:10]

    # Group by key
    groups: dict[str, list] = {}
    for r in rows:
        k = _key(r["name"] or r["handle"])
        groups.setdefault(k, []).append(dict(r))

    # Only act on groups with 2+ channels (different platforms)
    grouped = 0
    for key, channels in groups.items():
        if len(channels) < 2:
            continue
        platforms = {c["platform"] for c in channels}
        if len(platforms) < 2:
            continue   # same platform duplicates — skip

        # Create or find affiliate
        affiliate = await pool.fetchrow(
            "SELECT id FROM affiliates WHERE name = $1", key
        )
        if not affiliate:
            affiliate = await pool.fetchrow(
                "INSERT INTO affiliates (name) VALUES ($1) RETURNING id", key
            )
        affiliate_id = affiliate["id"]

        ids = [c["id"] for c in channels]
        await pool.execute(
            "UPDATE channels SET affiliate_id = $1 WHERE id = ANY($2::uuid[]) AND affiliate_id IS NULL",
            affiliate_id, ids,
        )
        grouped += 1

    return {"grouped_affiliates": grouped, "checked": len(rows)}
