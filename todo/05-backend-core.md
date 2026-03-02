[x]
# Prompt 05: Backend Core & Embedding Service

## Goal
Build the FastAPI application skeleton with database connection pooling (asyncpg + pgvector) and the embedding service (sentence-transformers loaded at startup).

## Context
- Location: `backend/app/`
- FastAPI with async, using lifespan for startup/shutdown
- Database: Supabase PostgreSQL via asyncpg (direct connection, port 5432)
- Embedding model: `all-MiniLM-L6-v2` loaded once at startup, inference via `asyncio.to_thread()`
- No auth — anonymous sessions

## Files to Implement

### 1. `backend/app/config.py` — Settings
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # postgresql://user:pass@host:5432/postgres
    embedding_model: str = "all-MiniLM-L6-v2"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    max_files_per_session: int = 5
    default_match_limit: int = 200  # return top 200 matches
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite dev server

    class Config:
        env_file = ".env"

settings = Settings()
```

### 2. `backend/app/database.py` — asyncpg pool + pgvector
Key implementation details:
- Use `asyncpg.create_pool()` with `min_size=2, max_size=5` (conservative for Supabase free tier)
- Register pgvector types on each connection via `init` callback: `await register_vector(conn)`
- Use `pgvector.asyncpg.register_vector` from the `pgvector` Python package
- For Supabase direct connection (port 5432), prepared statements work fine — no need to disable statement cache

```python
import asyncpg
from pgvector.asyncpg import register_vector

_pool: asyncpg.Pool | None = None

async def init_pool(database_url: str) -> asyncpg.Pool:
    """Initialize connection pool with pgvector support."""
    async def _init_conn(conn):
        await register_vector(conn)

    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=2,
        max_size=5,
        init=_init_conn,
        command_timeout=30,
    )
    return pool
```

Provide a `get_pool()` function and a FastAPI dependency `get_db()` that acquires a connection from the pool.

### 3. `backend/app/embeddings.py` — Sentence-transformers service
- Load model once at startup: `SentenceTransformer("all-MiniLM-L6-v2")`
- The model is ~80MB and uses ~150MB RAM when loaded
- On Oracle Cloud ARM (24GB RAM), this is trivial
- All encode calls must use `asyncio.to_thread()` in async handlers (CPU-bound)

```python
from sentence_transformers import SentenceTransformer
import numpy as np

_model: SentenceTransformer | None = None

def load_model(model_name: str = "all-MiniLM-L6-v2"):
    global _model
    _model = SentenceTransformer(model_name)
    return _model

def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Embed multiple texts. Returns (n, 384) array."""
    return _model.encode(texts, batch_size=batch_size,
                         show_progress_bar=False, normalize_embeddings=True)

def embed_query(text: str) -> np.ndarray:
    """Embed a single text. Returns (384,) array."""
    return _model.encode(text, normalize_embeddings=True)
```

### 4. `backend/app/main.py` — FastAPI app with lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await asyncio.to_thread(load_model, settings.embedding_model)
    app.state.pool = await init_pool(settings.database_url)
    yield
    # Shutdown
    await app.state.pool.close()

app = FastAPI(title="Relevancey", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from api/ modules
```

### 5. `.env` file (gitignored)
```
DATABASE_URL=postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres
```

## Running locally
```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Verification
- `uvicorn app.main:app` starts without errors
- Embedding model loads at startup (check logs)
- Database pool connects to Supabase (or local PostgreSQL for dev)
- `GET /docs` shows Swagger UI
- Health check endpoint `GET /health` returns `{"status": "ok", "model_loaded": true, "db_connected": true}`
