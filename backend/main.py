import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from db.pool import get_pool, close_pool
from api.channels import router as channels_router
from api.jobs import router as jobs_router
from api.queries import router as queries_router
from api.agent import router as agent_router
from api.enrich import router as enrich_router
from api.monitor import router as monitor_router
from api.competitors import router as competitors_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="AzBet Lead Search", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channels_router)
app.include_router(jobs_router)
app.include_router(queries_router)
app.include_router(agent_router)
app.include_router(enrich_router)
app.include_router(monitor_router)
app.include_router(competitors_router)

# Отдаём React билд в продакшне
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
