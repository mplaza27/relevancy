from __future__ import annotations

from typing import AsyncGenerator

import asyncpg
from pgvector.asyncpg import register_vector

_pool: asyncpg.Pool | None = None


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Register pgvector types on each new connection."""
    await register_vector(conn)


async def init_pool(database_url: str) -> asyncpg.Pool:
    """Initialize connection pool with pgvector support.

    Always use the direct Supabase connection (port 5432).
    The pooler (port 6543) breaks asyncpg prepared statement caching.
    """
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=2,
        max_size=5,
        init=_init_conn,
        command_timeout=30,
    )
    return _pool


def get_pool() -> asyncpg.Pool:
    """Return the global connection pool. Must be initialized first."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency: acquire a connection from the pool."""
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_pool() -> None:
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
