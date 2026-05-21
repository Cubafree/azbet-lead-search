from fastapi import APIRouter
from pydantic import BaseModel
from job_runner import run_autonomous_job

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    geo: str = "all"


@router.post("/run")
async def run_agent(body: AgentRunRequest):
    """Trigger autonomous agent: generates queries, searches, qualifies, drafts emails."""
    job_id = await run_autonomous_job(geo=body.geo)
    return {"job_id": job_id, "status": "started"}
