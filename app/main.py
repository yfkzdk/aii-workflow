"""FastAPI application factory with lifespan, CORS, and route mounting."""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.auth import authenticate

logger = logging.getLogger("app")

_start_time: float = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    _start_time = time.time()
    Path(settings.workflows_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    logger.info("AI Workflow Orchestrator started")
    yield
    logger.info("AI Workflow Orchestrator shutting down")


app = FastAPI(
    title="AI Workflow Orchestrator",
    description="LLM-powered multi-stage task orchestration engine",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import tasks, pipeline, artifacts, ws  # noqa: E402


@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


app.include_router(tasks.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(artifacts.router, prefix="/api")
app.include_router(ws.router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/api/health")
async def health():
    from app.deps import get_task_manager
    tm = get_task_manager()
    uptime = f"{time.time() - _start_time:.0f}s" if _start_time else "0s"
    return {
        "success": True,
        "version": "0.5.0",
        "uptime": uptime,
        "workflows_dir": settings.workflows_dir,
        "tasks_count": len(tm.list_tasks()),
    }
