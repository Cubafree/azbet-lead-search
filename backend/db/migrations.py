"""
Run once to create all tables: python -m db.migrations
"""
import asyncio
import asyncpg
from config import settings

SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Аффилиаты как бизнес-сущности (1 бренд/человек)
CREATE TABLE IF NOT EXISTS affiliates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT,
    status      TEXT NOT NULL DEFAULT 'new',   -- new | contacted | rejected | partner
    priority    TEXT,                           -- high | medium | low (из лучшего канала)
    niche       TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Каналы/площадки (TG, YouTube, Instagram, etc.)
CREATE TABLE IF NOT EXISTS channels (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id          UUID REFERENCES affiliates(id) ON DELETE SET NULL,

    platform              TEXT NOT NULL,   -- telegram | youtube | instagram | tiktok | web
    handle                TEXT NOT NULL,   -- @username, domain, channel_id
    UNIQUE (platform, handle),

    url                   TEXT,
    name                  TEXT,
    followers             BIGINT,
    description           TEXT,

    -- Контакты
    contact_email         TEXT,
    contact_telegram      TEXT,
    contact_other         TEXT,            -- WhatsApp, ссылка на форму

    -- AI-анализ
    language              TEXT,
    geo_focus             TEXT,
    niche                 TEXT,
    priority              TEXT,
    competitor_promo      TEXT,
    mentioned_competitors TEXT,
    ai_summary            TEXT,            -- почему актуален для нас

    -- Мета
    last_scraped_at       TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Очередь поисковых запросов
CREATE TABLE IF NOT EXISTS query_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text  TEXT NOT NULL,
    source_type TEXT NOT NULL,  -- telegram | youtube | seo
    geo         TEXT,           -- egypt | morocco | algeria | tunisia | libya | all
    language    TEXT DEFAULT 'en',
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | running | done | error
    result_count INT DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run_at TIMESTAMPTZ
);

-- Статус фоновых джобов (для UI прогресс-бара)
CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status      TEXT NOT NULL DEFAULT 'running',  -- running | done | error
    phase       TEXT,       -- searching | parsing | enriching | qualifying
    total       INT DEFAULT 0,
    processed   INT DEFAULT 0,
    new_found   INT DEFAULT 0,
    error_msg   TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

-- Estimated monthly visits (for web, AI-generated)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS estimated_monthly_visits BIGINT;

-- Outreach email draft (AI-generated for high/medium priority leads)
ALTER TABLE channels ADD COLUMN IF NOT EXISTS outreach_draft TEXT;

-- Archive flag — скрывает лид из выборки и энрича
ALTER TABLE channels ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

-- Contacted flag — менеджер отметил что уже работал с этим лидом
ALTER TABLE channels ADD COLUMN IF NOT EXISTS is_contacted BOOLEAN NOT NULL DEFAULT FALSE;

-- Индексы
CREATE INDEX IF NOT EXISTS idx_channels_platform    ON channels(platform);
CREATE INDEX IF NOT EXISTS idx_channels_priority    ON channels(priority);
CREATE INDEX IF NOT EXISTS idx_channels_affiliate   ON channels(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_channels_created     ON channels(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_affiliates_status    ON affiliates(status);
CREATE INDEX IF NOT EXISTS idx_jobs_started         ON jobs(started_at DESC);
"""


async def run():
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(SQL)
        print("✅ Migrations applied successfully")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
