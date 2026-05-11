"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.interviews import router as interviews_router
from app.api.projects import router as projects_router
from app.models.database import Base, async_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _run_migrations() -> None:
    """Apply schema changes that create_all won't handle (new columns on existing tables)."""
    from sqlalchemy import text
    async with async_engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS "
            "project_id UUID REFERENCES projects(id) ON DELETE SET NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE interviewee_profiles ADD COLUMN IF NOT EXISTS gender VARCHAR(64)"
        ))
        await conn.execute(text(
            "ALTER TABLE interviewee_profiles ADD COLUMN IF NOT EXISTS income_range VARCHAR(64)"
        ))
    logger.info("Migrations applied")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up — creating database tables if needed")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_migrations()
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down — disposing database engine")
    await async_engine.dispose()


app = FastAPI(
    title="Customer Research Interview Analyzer",
    description="Upload customer interviews (audio, video, or transcripts) and get structured insight reports.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(interviews_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
