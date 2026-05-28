"""
Competitor monitoring + stale lead refresh.
POST /api/monitor/competitors   — re-check competitor signals for high/medium leads
POST /api/monitor/refresh-stale — re-enrich leads last scraped > 30 days ago
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from db.pool import get_pool
from enrichers.pipeline import deep_enrich
from agents.scorer import score_channel, priority_from_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/monitor", tags=["monitor"])

COMPETITORS = ["1xbet", "melbet", "mostbet", "22bet", "1win", "betwinner"]
STALE_DAYS = 30


class CompetitorRequest(BaseModel):
    channel_ids: list[str] | None = None  # None = all high/medium, non-archived


class RefreshRequest(BaseModel):
    days_stale: int = STALE_DAYS
    limit: int = 100


@router.post("/competitors")
async def check_competitors(body: CompetitorRequest):
    """Re-run deep enrich on high/medium leads to refresh competitor signals."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "INSERT INTO jobs (status, phase) VALUES ('running', 'monitoring') RETURNING id"
    )
    job_id = str(row["id"])
    asyncio.create_task(_run_competitor_check(pool, job_id, body.channel_ids))
    return {"job_id": job_id, "status": "started"}


@router.post("/refresh-stale")
async def refresh_stale(body: RefreshRequest):
    """Re-enrich leads whose last_scraped_at is older than days_stale."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "INSERT INTO jobs (status, phase) VALUES ('running', 'refreshing') RETURNING id"
    )
    job_id = str(row["id"])
    asyncio.create_task(_run_refresh_stale(pool, job_id, body.days_stale, body.limit))
    return {"job_id": job_id, "status": "started"}


async def _upd(pool, job_id: str, **kw):
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kw))
    await pool.execute(f"UPDATE jobs SET {sets} WHERE id = $1", job_id, *kw.values())


async def _run_competitor_check(pool, job_id: str, channel_ids: list[str] | None):
    try:
        if channel_ids:
            rows = await pool.fetch(
                "SELECT * FROM channels WHERE id = ANY($1::uuid[]) AND is_archived = FALSE",
                channel_ids,
            )
        else:
            rows = await pool.fetch(
                """SELECT * FROM channels
                   WHERE is_archived = FALSE
                     AND priority IN ('high', 'medium')
                   ORDER BY last_monitored_at ASC NULLS FIRST
                   LIMIT 200"""
            )

        channels = [dict(r) for r in rows]
        total = len(channels)
        await _upd(pool, job_id, total=total, processed=0)
        logger.info("Competitor check job %s: %d channels", job_id, total)

        for i, ch in enumerate(channels):
            try:
                merged = await deep_enrich(ch)
                if merged:
                    # Check for new competitor signals in description
                    desc = (merged.get("description") or ch.get("description") or "").lower()
                    found = [c for c in COMPETITORS if c in desc]
                    mentioned = ", ".join(found) or None

                    updates: dict = {"last_monitored_at": datetime.now(timezone.utc)}
                    if found and not ch.get("mentioned_competitors"):
                        updates["mentioned_competitors"] = mentioned

                    # Refresh contact fields (COALESCE — don't overwrite)
                    for field in ("contact_email", "contact_telegram", "contact_other",
                                  "followers", "last_post_at", "audience_geo", "er_percent"):
                        if merged.get(field) and not ch.get(field):
                            updates[field] = merged[field]

                    # Re-score
                    merged_ch = {**ch, **updates}
                    updates["score"] = score_channel(merged_ch)

                    sets = ", ".join(f"{k} = ${i2+2}" for i2, k in enumerate(updates))
                    await pool.execute(
                        f"UPDATE channels SET {sets} WHERE id = $1",
                        ch["id"], *updates.values(),
                    )
            except Exception as e:
                logger.error("Competitor check error for %s: %s", ch.get("handle"), e)

            await _upd(pool, job_id, processed=i + 1)
            await asyncio.sleep(0.5)

        await _upd(pool, job_id, status="done", phase="done",
                   finished_at=datetime.now(timezone.utc))
        logger.info("Competitor check job %s done", job_id)

    except Exception as e:
        logger.exception("Competitor check job %s failed: %s", job_id, e)
        await _upd(pool, job_id, status="error", error_msg=str(e))


async def _run_refresh_stale(pool, job_id: str, days_stale: int, limit: int):
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_stale)
        rows = await pool.fetch(
            """SELECT * FROM channels
               WHERE is_archived = FALSE
                 AND (last_scraped_at < $1 OR last_scraped_at IS NULL)
               ORDER BY
                 CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                 last_scraped_at ASC NULLS FIRST
               LIMIT $2""",
            cutoff, limit,
        )

        channels = [dict(r) for r in rows]
        total = len(channels)
        await _upd(pool, job_id, total=total, processed=0)
        logger.info("Refresh-stale job %s: %d channels", job_id, total)

        for i, ch in enumerate(channels):
            try:
                merged = await deep_enrich(ch)
                if merged:
                    allowed = {
                        "contact_email", "contact_telegram", "contact_other",
                        "description", "followers", "last_post_at",
                        "audience_geo", "er_percent",
                    }
                    updates = {k: v for k, v in merged.items() if k in allowed and v is not None}
                    updates["last_scraped_at"] = datetime.now(timezone.utc)

                    # Re-score with fresh data
                    merged_ch = {**ch, **updates}
                    updates["score"] = score_channel(merged_ch)
                    new_priority = priority_from_score(updates["score"])
                    if ch.get("priority") != new_priority:
                        updates["priority"] = new_priority

                    sets = ", ".join(f"{k} = ${i2+2}" for i2, k in enumerate(updates))
                    await pool.execute(
                        f"UPDATE channels SET {sets} WHERE id = $1",
                        ch["id"], *updates.values(),
                    )
            except Exception as e:
                logger.error("Refresh-stale error for %s: %s", ch.get("handle"), e)

            await _upd(pool, job_id, processed=i + 1)
            await asyncio.sleep(0.5)

        await _upd(pool, job_id, status="done", phase="done",
                   finished_at=datetime.now(timezone.utc))
        logger.info("Refresh-stale job %s done", job_id)

    except Exception as e:
        logger.exception("Refresh-stale job %s failed: %s", job_id, e)
        await _upd(pool, job_id, status="error", error_msg=str(e))
