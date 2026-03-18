from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import close_pool, get_pool, init_pool
from app.embeddings import embed_query, is_loaded, load_model, is_cross_encoder_loaded, load_cross_encoder
from app.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: load model + init DB pool. Shutdown: close pool."""
    logger.info("Loading embedding model: %s", settings.embedding_model)
    await asyncio.to_thread(load_model, settings.embedding_model)
    logger.info("Embedding model loaded.")

    if settings.enable_cross_encoder:
        logger.info("Loading cross-encoder: %s", settings.cross_encoder_model)
        await asyncio.to_thread(load_cross_encoder, settings.cross_encoder_model)
        logger.info("Cross-encoder loaded.")

    if settings.database_url:
        logger.info("Initializing database pool ...")
        app.state.pool = await init_pool(settings.database_url)
        logger.info("Database pool ready.")
    else:
        logger.warning("DATABASE_URL not set — database features unavailable.")
        app.state.pool = None

    yield

    # Shutdown
    await close_pool()
    logger.info("Database pool closed.")


app = FastAPI(
    title="Relevancey",
    description="Match lecture materials to Anki flashcards by semantic similarity",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api import match, sync, upload  # noqa: E402

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(match.router, prefix="/api", tags=["match"])
app.include_router(sync.router, prefix="/api", tags=["sync"])


@app.get("/api/stats")
async def get_stats() -> dict:
    """Return note count and DB size for monitoring."""
    if app.state.pool is None:
        return {"anki_note_count": 0, "db_size_mb": 0}
    pool = get_pool()
    async with pool.acquire() as conn:
        note_count = await conn.fetchval("SELECT COUNT(*) FROM anki_notes")
        db_size_mb = await conn.fetchval(
            "SELECT pg_database_size(current_database()) / 1024 / 1024"
        )
    return {"anki_note_count": note_count, "db_size_mb": db_size_mb}


@app.get("/health")
async def health_check() -> dict:
    """Health check: verify model and database are ready."""
    db_connected = False
    if app.state.pool is not None:
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_connected = True
        except Exception:
            db_connected = False

    return {
        "status": "ok",
        "model_loaded": is_loaded(),
        "cross_encoder_loaded": is_cross_encoder_loaded(),
        "db_connected": db_connected,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
