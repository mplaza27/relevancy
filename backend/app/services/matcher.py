from __future__ import annotations

from uuid import UUID

import asyncpg
import numpy as np


async def run_matching(
    pool: asyncpg.Pool,
    session_id: UUID,
    chunk_embeddings: np.ndarray,
    match_limit_per_chunk: int = 50,
) -> list[dict]:
    """Match document chunk embeddings against Anki notes via pgvector.

    For each chunk, query top-K similar notes. Aggregate across all chunks by
    keeping the highest similarity for each note. Insert results into DB.

    Returns list of match dicts sorted by similarity descending.
    """
    all_matches: dict[int, dict] = {}

    async with pool.acquire() as conn:
        for emb in chunk_embeddings:
            rows = await conn.fetch(
                """
                SELECT note_id, notetype, deck, text, extra, tags, raw_fields,
                       1.0 - (embedding <=> $1::vector) AS similarity
                FROM anki_notes
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                emb.tolist(),
                match_limit_per_chunk,
            )

            for row in rows:
                nid = row["note_id"]
                sim = float(row["similarity"])
                if nid not in all_matches or sim > all_matches[nid]["similarity"]:
                    all_matches[nid] = dict(row)

        # Sort by similarity descending
        results = sorted(all_matches.values(), key=lambda x: x["similarity"], reverse=True)

        # Store in match_results for retrieval
        if results:
            await conn.executemany(
                """
                INSERT INTO match_results (session_id, note_id, similarity)
                VALUES ($1, $2, $3)
                """,
                [(session_id, r["note_id"], r["similarity"]) for r in results],
            )

    return results
