"""
Batch enrichment: глубокий поиск контактов + генерация писем.
POST /api/enrich/run  — запускает фоновый джоб
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from db.pool import get_pool
from enrichers import telegram_deep, tgstat_api, youtube_api, contact_search
from agents.email_drafter import draft_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enrich", tags=["enrich"])


class EnrichRequest(BaseModel):
    channel_ids: list[str] | None = None   # None = все не-архивные без контактов


@router.post("/run")
async def run_enrich(body: EnrichRequest):
    """Deep contact enrichment + email drafting for non-archived leads."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO jobs (status, phase) VALUES ('running', 'enriching') RETURNING id"
    )
    job_id = str(row["id"])
    asyncio.create_task(_execute_enrich(pool, job_id, body.channel_ids))
    return {"job_id": job_id, "status": "started"}


async def _execute_enrich(pool, job_id: str, channel_ids: list[str] | None):
    async def upd(**kw):
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kw))
        await pool.execute(f"UPDATE jobs SET {sets} WHERE id = $1", job_id, *kw.values())

    try:
        # Fetch channels to enrich
        if channel_ids:
            rows = await pool.fetch(
                "SELECT * FROM channels WHERE id = ANY($1::uuid[]) AND is_archived = FALSE",
                channel_ids,
            )
        else:
            # Все не-архивные без контактов
            rows = await pool.fetch(
                """SELECT * FROM channels
                   WHERE is_archived = FALSE
                     AND contact_email IS NULL
                     AND contact_telegram IS NULL
                     AND contact_other IS NULL
                   ORDER BY
                     CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                     created_at DESC
                   LIMIT 200"""
            )

        channels = [dict(r) for r in rows]
        total = len(channels)
        logger.info("Enrich job %s: %d channels to process", job_id, total)
        await upd(phase="enriching", total=total, processed=0)

        for i, ch in enumerate(channels):
            try:
                merged = await _deep_enrich(ch)
                if merged:
                    await _update_channel_contacts(pool, ch["id"], merged)
                    ch.update({k: v for k, v in merged.items() if v})

                # Generate email draft if high/medium and not already drafted
                if ch.get("priority") in ("high", "medium") and not ch.get("outreach_draft"):
                    draft = await draft_email(ch)
                    if draft:
                        await pool.execute(
                            "UPDATE channels SET outreach_draft = $1 WHERE id = $2",
                            draft, ch["id"],
                        )

            except Exception as e:
                logger.error("Enrich error for %s: %s", ch.get("handle"), e)

            await upd(processed=i + 1)
            await asyncio.sleep(0.5)

        await upd(
            status="done", phase="done",
            finished_at=datetime.now(timezone.utc),
        )
        logger.info("Enrich job %s done", job_id)

    except Exception as e:
        logger.exception("Enrich job %s failed: %s", job_id, e)
        await upd(status="error", error_msg=str(e))


async def _deep_enrich(ch: dict) -> dict:
    """Run all available enrichers for a channel, return merged results."""
    platform = ch.get("platform", "")
    handle = ch.get("handle", "")
    url = ch.get("url", "")
    result: dict = {}

    if platform == "telegram":
        # 1. Telethon (get admins, scan messages)
        r = await telegram_deep.enrich_channel(handle)
        result.update({k: v for k, v in r.items() if v})

        # 2. TGStat (subscribers + sometimes contact)
        if not result.get("contact_email"):
            r = await tgstat_api.enrich_channel(handle)
            result.update({k: v for k, v in r.items() if v and k not in result})

    elif platform == "youtube":
        # YouTube Data API
        channel_id = ch.get("handle", "")
        r = await youtube_api.enrich_channel(channel_id, url)
        result.update({k: v for k, v in r.items() if v})

    # Cross-search via Serper for any platform without contacts after above
    has_contact = result.get("contact_email") or result.get("contact_telegram") or result.get("contact_other")
    if not has_contact:
        r = await contact_search.find_contacts(ch)
        result.update({k: v for k, v in r.items() if v})

    return result


async def _update_channel_contacts(pool, channel_id: str, data: dict):
    allowed = {
        "contact_email", "contact_telegram", "contact_other",
        "description", "followers", "geo_focus",
    }
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not updates:
        return
    sets = ", ".join(f"{k} = COALESCE({k}, ${i+2})" for i, k in enumerate(updates))
    await pool.execute(
        f"UPDATE channels SET {sets} WHERE id = $1",
        channel_id, *updates.values(),
    )
