"""
Competitor intelligence API.
GET  /api/competitors              — list competitors with metrics
GET  /api/competitors/{name}       — single competitor detail
GET  /api/competitors/{name}/signals — recent signals
GET  /api/competitors/overlap      — our leads promoting competitors
GET  /api/competitors/insights     — AI-generated insights
POST /api/competitors/scan         — trigger background scan job
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel

from db.pool import get_pool
from scrapers.competitor_monitor import scan_all_competitors, scan_competitor
from agents.competitor_insights import generate_insights, generate_overlap_insights

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/competitors", tags=["competitors"])

SIGNAL_WINDOW_DAYS = 30


class ScanRequest(BaseModel):
    geo: str = "all"
    competitor_name: str | None = None   # None = all


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
async def list_competitors():
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM competitors ORDER BY affiliate_count DESC NULLS LAST")

    result = []
    for row in rows:
        comp = dict(row)
        # Count signals from last 30 days
        since = datetime.now(timezone.utc) - timedelta(days=SIGNAL_WINDOW_DAYS)
        sig_count = await pool.fetchval(
            "SELECT COUNT(*) FROM competitor_signals WHERE competitor_name = $1 AND created_at > $2",
            comp["name"], since,
        )
        # Count our leads that mention this competitor
        overlap = await pool.fetchval(
            "SELECT COUNT(*) FROM channels WHERE is_archived = FALSE "
            "AND mentioned_competitors ILIKE $1",
            f"%{comp['name']}%",
        )
        comp["signals_30d"] = sig_count
        comp["our_overlap"] = overlap
        result.append(comp)

    return result


@router.get("/overlap")
async def get_overlap(limit: int = Query(100, le=200)):
    """Our leads that are promoting competitors — highest overlap risk."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, platform, handle, name, followers, priority, score,
                  mentioned_competitors, competitor_promo, geo_focus,
                  contact_email, contact_telegram, url
           FROM channels
           WHERE is_archived = FALSE
             AND (mentioned_competitors IS NOT NULL OR competitor_promo IS NOT NULL)
           ORDER BY
             CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
             followers DESC NULLS LAST
           LIMIT $1""",
        limit,
    )
    channels = [dict(r) for r in rows]

    # AI strategic note (fast, cached enough)
    note = await generate_overlap_insights(channels[:20])

    return {"channels": channels, "total": len(channels), "ai_note": note}


@router.get("/insights")
async def get_insights():
    """AI-generated competitive intelligence insights."""
    pool = await get_pool()

    # Aggregate competitor metrics
    comp_rows = await pool.fetch("SELECT * FROM competitors ORDER BY affiliate_count DESC")
    our_stats_rows = await pool.fetch(
        "SELECT platform, COUNT(*) as cnt FROM channels "
        "WHERE is_archived = FALSE GROUP BY platform"
    )
    our_total = await pool.fetchval("SELECT COUNT(*) FROM channels WHERE is_archived = FALSE")

    competitors_data = []
    for row in comp_rows:
        comp = dict(row)
        # Get recent signals
        since = datetime.now(timezone.utc) - timedelta(days=30)
        signals = await pool.fetch(
            "SELECT signal_type, geo, description FROM competitor_signals "
            "WHERE competitor_name = $1 AND created_at > $2 ORDER BY created_at DESC LIMIT 10",
            comp["name"], since,
        )
        competitors_data.append({
            "name": comp["name"],
            "affiliate_count": comp["affiliate_count"] or 0,
            "last_scanned_at": comp["last_scanned_at"].isoformat() if comp["last_scanned_at"] else None,
            "recent_signals": [dict(s) for s in signals],
        })

    our_stats = {
        "total_leads": our_total,
        "by_platform": {r["platform"]: r["cnt"] for r in our_stats_rows},
    }

    insights = await generate_insights(competitors_data, our_stats)
    return {"insights": insights, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/{name}/signals")
async def get_signals(name: str, days: int = Query(30, le=90), limit: int = Query(50, le=200)):
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await pool.fetch(
        """SELECT cs.*, c.handle, c.platform, c.followers
           FROM competitor_signals cs
           LEFT JOIN channels c ON c.id = cs.channel_id
           WHERE cs.competitor_name = $1 AND cs.created_at > $2
           ORDER BY cs.created_at DESC
           LIMIT $3""",
        name, since, limit,
    )
    return [dict(r) for r in rows]


@router.get("/{name}")
async def get_competitor(name: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM competitors WHERE name = $1", name)
    if not row:
        return {"error": "not found"}

    comp = dict(row)

    # Channels in our DB promoting this competitor
    overlap = await pool.fetch(
        """SELECT id, platform, handle, name AS channel_name, followers, priority, score,
                  competitor_promo, geo_focus, contact_email, contact_telegram
           FROM channels
           WHERE is_archived = FALSE AND mentioned_competitors ILIKE $1
           ORDER BY followers DESC NULLS LAST
           LIMIT 50""",
        f"%{name}%",
    )

    # Recent signals
    since = datetime.now(timezone.utc) - timedelta(days=30)
    signals = await pool.fetch(
        "SELECT * FROM competitor_signals WHERE competitor_name = $1 AND created_at > $2 "
        "ORDER BY created_at DESC LIMIT 20",
        name, since,
    )

    comp["overlap_channels"] = [dict(r) for r in overlap]
    comp["recent_signals"] = [dict(r) for r in signals]
    return comp


@router.post("/scan")
async def trigger_scan(body: ScanRequest):
    """Launch background competitor scan job."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO jobs (status, phase) VALUES ('running', 'competitor_scan') RETURNING id"
    )
    job_id = str(row["id"])
    asyncio.create_task(_run_scan(pool, job_id, body.geo, body.competitor_name))
    return {"job_id": job_id, "status": "started"}


# ── Background task ─────────────────────────────────────────────────────────

async def _upd(pool, job_id: str, **kw):
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kw))
    await pool.execute(f"UPDATE jobs SET {sets} WHERE id = $1", job_id, *kw.values())


async def _run_scan(pool, job_id: str, geo: str, competitor_name: str | None):
    try:
        if competitor_name:
            row = await pool.fetchrow("SELECT * FROM competitors WHERE name = $1", competitor_name)
            competitors = [dict(row)] if row else []
        else:
            rows = await pool.fetch("SELECT * FROM competitors ORDER BY name")
            competitors = [dict(r) for r in rows]

        await _upd(pool, job_id, total=len(competitors), processed=0)

        # Load current known handles to detect NEW affiliates vs already in DB
        known = {
            (r["platform"], r["handle"])
            for r in await pool.fetch("SELECT platform, handle FROM channels")
        }

        for i, comp in enumerate(competitors):
            try:
                result = await scan_competitor(comp, geo)
                await _upd(pool, job_id, phase=f"scanning_{comp['name']}")

                new_affiliates = 0
                active_promos = result["promo_codes"]

                # Process TG channels
                for ch in result["tg_channels"] + result["yt_channels"]:
                    key = (ch["platform"], ch["handle"])
                    is_new = key not in known

                    # Upsert into channels with competitor tag
                    await pool.execute(
                        """INSERT INTO channels
                           (platform, handle, url, name, description, followers,
                            language, geo_focus, mentioned_competitors, last_scraped_at)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,NOW())
                           ON CONFLICT (platform, handle) DO UPDATE
                             SET mentioned_competitors = EXCLUDED.mentioned_competitors,
                                 last_scraped_at = NOW()""",
                        ch["platform"], ch["handle"], ch.get("url"), ch.get("name"),
                        ch.get("description"), ch.get("followers"),
                        ch.get("language"), ch.get("geo_focus"),
                        comp["name"],
                    )

                    if is_new:
                        new_affiliates += 1
                        known.add(key)
                        # Record signal
                        await pool.execute(
                            """INSERT INTO competitor_signals
                               (competitor_name, signal_type, description, geo, data)
                               VALUES ($1, 'new_affiliate', $2, $3, $4)""",
                            comp["name"],
                            f"New affiliate found: @{ch['handle']} ({ch['platform']})",
                            ch.get("geo_focus"),
                            {"handle": ch["handle"], "followers": ch.get("followers")},
                        )

                # Record new promo codes as signals
                for code in active_promos:
                    exists = await pool.fetchval(
                        "SELECT 1 FROM competitor_signals "
                        "WHERE competitor_name=$1 AND signal_type='new_promo' "
                        "AND data->>'code' = $2",
                        comp["name"], code,
                    )
                    if not exists:
                        await pool.execute(
                            """INSERT INTO competitor_signals
                               (competitor_name, signal_type, description, data)
                               VALUES ($1, 'new_promo', $2, $3)""",
                            comp["name"],
                            f"Promo code detected: {code}",
                            {"code": code},
                        )

                # Check our high/medium leads switching to this competitor
                switched = await pool.fetch(
                    """SELECT id, handle, platform FROM channels
                       WHERE is_archived = FALSE
                         AND priority IN ('high','medium')
                         AND mentioned_competitors ILIKE $1
                         AND id NOT IN (
                           SELECT channel_id FROM competitor_signals
                           WHERE competitor_name = $2
                             AND signal_type = 'lead_switched'
                             AND channel_id IS NOT NULL
                         )""",
                    f"%{comp['name']}%", comp["name"],
                )
                for ch in switched:
                    await pool.execute(
                        """INSERT INTO competitor_signals
                           (competitor_name, signal_type, description, channel_id, data)
                           VALUES ($1, 'lead_switched', $2, $3, $4)""",
                        comp["name"],
                        f"Our lead @{ch['handle']} ({ch['platform']}) promotes this competitor",
                        ch["id"],
                        {"handle": ch["handle"], "platform": ch["platform"]},
                    )

                # Update competitor aggregate
                total_affiliates = await pool.fetchval(
                    "SELECT COUNT(*) FROM channels WHERE is_archived = FALSE "
                    "AND mentioned_competitors ILIKE $1",
                    f"%{comp['name']}%",
                )
                await pool.execute(
                    "UPDATE competitors SET affiliate_count=$1, last_scanned_at=NOW() WHERE name=$2",
                    total_affiliates, comp["name"],
                )

                logger.info(
                    "Scan %s done: %d new affiliates, %d promos",
                    comp["name"], new_affiliates, len(active_promos),
                )

            except Exception as e:
                logger.error("Scan error for %s: %s", comp["name"], e)

            await _upd(pool, job_id, processed=i + 1)
            import asyncio as _a; await _a.sleep(1)

        await _upd(pool, job_id, status="done", phase="done",
                   finished_at=datetime.now(timezone.utc))

    except Exception as e:
        logger.exception("Competitor scan job %s failed: %s", job_id, e)
        await _upd(pool, job_id, status="error", error_msg=str(e))
