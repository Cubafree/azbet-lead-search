from fastapi import APIRouter
from pydantic import BaseModel
from db.pool import get_pool
from job_runner import run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class QueryItem(BaseModel):
    query_text: str
    source_type: str        # telegram | youtube | seo
    geo: str = "all"
    language: str = "en"


class RunRequest(BaseModel):
    queries: list[QueryItem] | None = None   # None = берём из query_queue


@router.post("/run")
async def trigger_job(body: RunRequest):
    queries = [q.model_dump() for q in body.queries] if body.queries else None
    job_id = await run_job(queries)
    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def job_status(job_id: str):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE id = $1", job_id)
    if not row:
        return {"error": "not found"}
    return dict(row)


@router.get("/latest")
async def latest_job():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs ORDER BY started_at DESC LIMIT 1")
    return dict(row) if row else {}
