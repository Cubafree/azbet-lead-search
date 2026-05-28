"""
One-off cleanup: archive existing leads that are now filtered by the
activity-filter and 1k-subscriber rules added after the first batch.

Run from project root:
  python scripts/cleanup_inactive_leads.py [--dry-run]

What it does:
  1. Archive TG channels with known followers < 1000
  2. Archive TG/YT channels where last_post_at is older than 14 days
     (skips channels where last_post_at is NULL — can't judge them)
  3. Print a summary
"""
import asyncio
import argparse
import sys
from datetime import datetime, timezone, timedelta

import asyncpg

# Inline the DB URL so the script runs outside the FastAPI context
import os
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Try loading from .env in backend/
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var not set", file=sys.stderr)
    sys.exit(1)

INACTIVE_DAYS = 14
TG_MIN_FOLLOWERS = 1_000


async def main(dry_run: bool):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # ── 1. Low-follower TG channels ──────────────────────────────────────
        low_follower = await conn.fetch(
            """SELECT id, handle, followers FROM channels
               WHERE platform = 'telegram'
                 AND is_archived = FALSE
                 AND followers IS NOT NULL
                 AND followers < $1""",
            TG_MIN_FOLLOWERS,
        )
        print(f"Low-follower TG channels (<{TG_MIN_FOLLOWERS}): {len(low_follower)}")
        for r in low_follower[:10]:
            print(f"  @{r['handle']} — {r['followers']} followers")
        if len(low_follower) > 10:
            print(f"  ... and {len(low_follower)-10} more")

        # ── 2. Inactive TG/YT channels ───────────────────────────────────────
        cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
        inactive = await conn.fetch(
            """SELECT id, handle, platform, last_post_at FROM channels
               WHERE platform IN ('telegram', 'youtube')
                 AND is_archived = FALSE
                 AND last_post_at IS NOT NULL
                 AND last_post_at < $1""",
            cutoff,
        )
        print(f"\nInactive TG/YT channels (no post >{INACTIVE_DAYS} days): {len(inactive)}")
        for r in inactive[:10]:
            days_ago = (datetime.now(timezone.utc) - r["last_post_at"]).days
            print(f"  [{r['platform']}] @{r['handle']} — last post {days_ago}d ago")
        if len(inactive) > 10:
            print(f"  ... and {len(inactive)-10} more")

        # ── 3. Archive ────────────────────────────────────────────────────────
        all_ids = (
            [str(r["id"]) for r in low_follower] +
            [str(r["id"]) for r in inactive]
        )
        # Deduplicate
        unique_ids = list(dict.fromkeys(all_ids))
        print(f"\nTotal to archive: {len(unique_ids)}")

        if dry_run:
            print("DRY RUN — no changes made.")
            return

        if not unique_ids:
            print("Nothing to archive.")
            return

        archived = await conn.execute(
            "UPDATE channels SET is_archived = TRUE WHERE id = ANY($1::uuid[])",
            unique_ids,
        )
        print(f"Archived: {archived}")

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive inactive / low-follower leads")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be archived without changing anything")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
