from fastapi import APIRouter
from pydantic import BaseModel
from db.pool import get_pool

router = APIRouter(prefix="/api/queries", tags=["queries"])


class QueryCreate(BaseModel):
    query_text: str
    source_type: str
    geo: str = "all"
    language: str = "en"


@router.get("")
async def list_queries():
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM query_queue ORDER BY created_at DESC")
    return [dict(r) for r in rows]


@router.post("")
async def create_query(body: QueryCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO query_queue (query_text, source_type, geo, language)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        body.query_text, body.source_type, body.geo, body.language,
    )
    return dict(row)


@router.delete("/{query_id}")
async def delete_query(query_id: str):
    pool = await get_pool()
    await pool.execute("DELETE FROM query_queue WHERE id = $1", query_id)
    return {"ok": True}


@router.post("/{query_id}/reset")
async def reset_query(query_id: str):
    """Сбрасывает статус на pending для повторного запуска."""
    pool = await get_pool()
    await pool.execute(
        "UPDATE query_queue SET status='pending' WHERE id=$1", query_id
    )
    return {"ok": True}
