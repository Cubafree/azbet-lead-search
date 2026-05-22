"""
Основной пайплайн: поиск → парсинг → обогащение → AI-квалификация → сохранение в БД.

Запускается как фоновый asyncio таск из API эндпоинта.
"""
import asyncio
import logging
from datetime import datetime, timezone

import asyncpg

from db.pool import get_pool
from scrapers import serper, telegram, youtube, web
from enrichers import ai_qualify
from agents.query_generator import generate_queries
from agents.mena_filter import is_mena_relevant

logger = logging.getLogger(__name__)

# Источники, которые скипаем при повторном скрапинге
# Загружаем один раз в начале джоба в память
_known_handles: set[tuple[str, str]] = set()


async def _load_known_handles(pool: asyncpg.Pool):
    rows = await pool.fetch("SELECT platform, handle FROM channels")
    return {(r["platform"], r["handle"]) for r in rows}


async def _create_job(pool: asyncpg.Pool) -> str:
    row = await pool.fetchrow(
        "INSERT INTO jobs (status, phase) VALUES ('running', 'searching') RETURNING id"
    )
    return str(row["id"])


async def _update_job(pool: asyncpg.Pool, job_id: str, **kwargs):
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(kwargs))
    values = list(kwargs.values())
    await pool.execute(
        f"UPDATE jobs SET {sets} WHERE id = $1", job_id, *values
    )


async def _upsert_channel(pool: asyncpg.Pool, ch: dict) -> bool:
    """
    Вставляет новый канал. Возвращает True если вставили новую запись.
    При конфликте (platform, handle) — пропускаем (ON CONFLICT DO NOTHING).
    """
    result = await pool.execute(
        """
        INSERT INTO channels (
            platform, handle, url, name, description, followers,
            contact_email, contact_telegram, contact_other,
            language, geo_focus, niche, priority,
            mentioned_competitors, competitor_promo, ai_summary,
            estimated_monthly_visits, outreach_draft,
            last_scraped_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9,
            $10, $11, $12, $13,
            $14, $15, $16,
            $17, $18,
            NOW()
        )
        ON CONFLICT (platform, handle) DO NOTHING
        """,
        ch.get("platform"), ch.get("handle"), ch.get("url"), ch.get("name"),
        ch.get("description"), ch.get("followers"),
        ch.get("contact_email"), ch.get("contact_telegram"), ch.get("contact_other"),
        ch.get("language"), ch.get("geo_focus"), ch.get("niche"), ch.get("priority"),
        ch.get("mentioned_competitors"), ch.get("competitor_promo"), ch.get("ai_summary"),
        ch.get("estimated_monthly_visits"), ch.get("outreach_draft"),
    )
    return result == "INSERT 0 1"


async def run_job(queries: list[dict] | None = None) -> str:
    """
    queries: список {query_text, source_type, geo, language}
    Если None — берём все pending из query_queue.
    Возвращает job_id.
    """
    pool = await get_pool()
    job_id = await _create_job(pool)
    logger.info(f"Job {job_id} started")

    asyncio.create_task(_execute_job(pool, job_id, queries))
    return job_id


async def _execute_job(pool: asyncpg.Pool, job_id: str, queries: list[dict] | None):
    try:
        # 1. Загружаем известные хендлы (дедуп уровень 2)
        known = await _load_known_handles(pool)
        logger.info(f"Loaded {len(known)} known handles")

        # 2. Берём запросы
        if queries is None:
            rows = await pool.fetch(
                "SELECT * FROM query_queue WHERE status = 'pending' ORDER BY created_at"
            )
            queries = [dict(r) for r in rows]

        # Разворачиваем каждый запрос в 3 источника: telegram + youtube + seo
        expanded: list[dict] = []
        for q in queries:
            geo = q.get("geo", "all")
            text = q["query_text"]
            for source_type in ["telegram", "youtube", "seo"]:
                expanded.append({**q, "source_type": source_type, "geo": geo, "query_text": text})

        await _update_job(pool, job_id, phase="searching", total=len(expanded))

        all_channels: list[dict] = []

        # 3. Поиск через Serper по всем источникам
        for i, q in enumerate(expanded):
            try:
                # Для каждого источника ищем на всех языках (en + ar)
                for lang in ["en", "ar"]:
                    data = await serper.search(
                        q["query_text"], q["source_type"], q.get("geo", "all"), lang
                    )
                    source_type = q["source_type"]

                    if source_type == "telegram":
                        parsed = telegram.parse_serper_results(data, lang, q.get("geo", "all"))
                    elif source_type == "youtube":
                        parsed = youtube.parse_serper_results(data, lang, q.get("geo", "all"))
                    else:
                        parsed = web.parse_serper_results(data, lang, q.get("geo", "all"))

                    all_channels.extend(parsed)

                # Обновляем статус запроса в очереди (только для оригинальных, не expanded)
                if "id" in q and q["source_type"] == "telegram":
                    await pool.execute(
                        "UPDATE query_queue SET status='done', last_run_at=NOW() WHERE id=$1",
                        q["id"]
                    )

            except Exception as e:
                logger.error(f"Search error for query '{q['query_text']}' [{q['source_type']}]: {e}")

            await _update_job(pool, job_id, processed=i + 1)

        # 4. Дедуп внутри батча + против БД
        unique_channels = []
        seen_in_batch: set[tuple[str, str]] = set()
        for ch in all_channels:
            key = (ch["platform"], ch["handle"])
            if key in known or key in seen_in_batch:
                continue
            seen_in_batch.add(key)
            unique_channels.append(ch)

        logger.info(f"New channels after dedup: {len(unique_channels)} (from {len(all_channels)} total)")

        # 5. Обогащение + AI квалификация
        await _update_job(pool, job_id, phase="enriching", total=len(unique_channels), processed=0)

        new_count = 0
        for i, ch in enumerate(unique_channels):
            try:
                # Обогащение
                enriched = await _enrich(ch)
                ch.update({k: v for k, v in enriched.items() if v is not None})

                # AI квалификация
                await _update_job(pool, job_id, phase="qualifying")
                qual = await ai_qualify.qualify(ch)
                ch.update(qual)

                # Сохраняем
                inserted = await _upsert_channel(pool, ch)
                if inserted:
                    new_count += 1
                    known.add((ch["platform"], ch["handle"]))

            except Exception as e:
                logger.error(f"Enrich/qualify error for {ch.get('handle')}: {e}")

            await _update_job(pool, job_id, processed=i + 1, new_found=new_count)
            # Небольшая пауза чтобы не флудить OpenAI
            await asyncio.sleep(0.3)

        await _update_job(
            pool, job_id,
            status="done",
            phase="done",
            new_found=new_count,
            finished_at=datetime.now(timezone.utc),
        )
        logger.info(f"Job {job_id} done. New channels: {new_count}")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        await _update_job(pool, job_id, status="error", error_msg=str(e))


async def run_autonomous_job(geo: str = "all") -> str:
    """
    Полностью автономный режим:
    1. OpenAI генерирует поисковые запросы
    2. Serper ищет по всем источникам и языкам
    3. MENA-фильтр отсекает нерелевантные каналы
    4. AI-квалификация + черновик письма для high/medium лидов
    """
    pool = await get_pool()
    job_id = await _create_job(pool)
    logger.info(f"Autonomous job {job_id} started for geo={geo}")
    asyncio.create_task(_execute_autonomous_job(pool, job_id, geo))
    return job_id


async def _execute_autonomous_job(pool, job_id: str, geo: str):
    try:
        # 1. Генерируем запросы через OpenAI
        await _update_job(pool, job_id, phase="generating_queries")
        queries = await generate_queries(geo)
        logger.info(f"Job {job_id}: generated {len(queries)} queries for geo={geo}")

        # 2. Записываем запросы в query_queue для отображения в UI
        for q in queries:
            try:
                await pool.execute(
                    """INSERT INTO query_queue (query_text, source_type, geo, language, status)
                       VALUES ($1, 'all', $2, 'all', 'running')
                       ON CONFLICT DO NOTHING""",
                    q["query_text"], q.get("geo", geo),
                )
            except Exception:
                pass

        # 3. Загружаем известные хендлы
        known = await _load_known_handles(pool)

        # 4. Разворачиваем в источники
        expanded: list[dict] = []
        for q in queries:
            for source_type in ["telegram", "youtube", "seo"]:
                expanded.append({**q, "source_type": source_type})

        await _update_job(pool, job_id, phase="searching", total=len(expanded))

        all_channels: list[dict] = []
        for i, q in enumerate(expanded):
            try:
                for lang in ["en", "ar"]:
                    data = await serper.search(
                        q["query_text"], q["source_type"], q.get("geo", geo), lang
                    )
                    source_type = q["source_type"]
                    if source_type == "telegram":
                        parsed = telegram.parse_serper_results(data, lang, q.get("geo", geo))
                    elif source_type == "youtube":
                        parsed = youtube.parse_serper_results(data, lang, q.get("geo", geo))
                    else:
                        parsed = web.parse_serper_results(data, lang, q.get("geo", geo))
                    all_channels.extend(parsed)
            except Exception as e:
                logger.error(f"Search error [{q['source_type']}] '{q['query_text']}': {e}")
            await _update_job(pool, job_id, processed=i + 1)

        # 5. Дедуп
        unique_channels = []
        seen: set[tuple[str, str]] = set()
        for ch in all_channels:
            key = (ch["platform"], ch["handle"])
            if key in known or key in seen:
                continue
            seen.add(key)
            unique_channels.append(ch)

        logger.info(f"Job {job_id}: {len(unique_channels)} unique channels after dedup")

        # 6. MENA pre-filter
        mena_channels = [ch for ch in unique_channels if is_mena_relevant(ch)]
        filtered_out = len(unique_channels) - len(mena_channels)
        logger.info(f"Job {job_id}: MENA filter removed {filtered_out}, kept {len(mena_channels)}")

        await _update_job(pool, job_id, phase="enriching", total=len(mena_channels), processed=0)

        new_count = 0
        for i, ch in enumerate(mena_channels):
            try:
                # Обогащение
                enriched = await _enrich(ch)
                ch.update({k: v for k, v in enriched.items() if v is not None})

                # AI квалификация
                await _update_job(pool, job_id, phase="qualifying")
                qual = await ai_qualify.qualify(ch)
                ch.update(qual)

                # MENA check после AI qualify — отсекаем если AI определил не-MENA
                ai_geo = (ch.get("geo_focus") or "").lower()
                if ai_geo and ai_geo not in {
                    "egypt", "morocco", "algeria", "tunisia", "libya",
                    "mena", "arab", "maghreb", "null", ""
                }:
                    logger.debug(f"Post-qualify MENA filter: skip {ch.get('handle')} geo={ai_geo}")
                    continue

                # Сохраняем (черновик письма генерится отдельно через Enrich Leads)
                inserted = await _upsert_channel(pool, ch)
                if inserted:
                    new_count += 1
                    known.add((ch["platform"], ch["handle"]))

            except Exception as e:
                logger.error(f"Enrich/qualify error for {ch.get('handle')}: {e}")

            await _update_job(pool, job_id, processed=i + 1, new_found=new_count)
            await asyncio.sleep(0.3)

        # Помечаем запросы как выполненные
        await pool.execute(
            "UPDATE query_queue SET status='done', last_run_at=NOW() WHERE status='running'"
        )

        await _update_job(
            pool, job_id,
            status="done", phase="done",
            new_found=new_count,
            finished_at=datetime.now(timezone.utc),
        )
        logger.info(f"Autonomous job {job_id} done. New channels: {new_count}")

    except Exception as e:
        logger.exception(f"Autonomous job {job_id} failed: {e}")
        await _update_job(pool, job_id, status="error", error_msg=str(e))


async def _enrich(ch: dict) -> dict:
    """Обогащение в зависимости от платформы."""
    platform = ch.get("platform")
    try:
        if platform == "telegram":
            return await telegram.enrich_channel(ch["handle"])
        elif platform == "youtube" and ch.get("url"):
            return await youtube.enrich_channel(ch["url"])
        elif platform == "web" and ch.get("url"):
            return await web.enrich_site(ch["url"])
    except Exception as e:
        logger.warning(f"Enrich failed for {ch.get('handle')}: {e}")
    return {}
