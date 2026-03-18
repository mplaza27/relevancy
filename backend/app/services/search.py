"""Hybrid search: semantic (pgvector) + BM25 (tsvector) with RRF fusion."""
from __future__ import annotations

import logging
import re

import asyncpg
import numpy as np

logger = logging.getLogger(__name__)

# Standard RRF constant (k=60 is the default from the original paper)
_RRF_K = 60

# English stop words for BM25 query construction
_STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "my", "no", "not", "of", "on", "or", "our", "she",
    "so", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "to", "up", "us", "was", "we", "what", "when", "which",
    "who", "will", "with", "would", "you", "your",
})

# Only keep alphanumeric tokens
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def extract_search_terms(text: str, max_terms: int = 20) -> str | None:
    """Extract significant terms from text for BM25 tsquery.

    Tokenizes, removes stop words, deduplicates, and returns OR-joined terms
    suitable for to_tsquery('english', ...).

    Returns None if no significant terms found.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    seen: set[str] = set()
    terms: list[str] = []
    for tok in tokens:
        if tok in _STOP_WORDS or len(tok) < 2 or tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)
        if len(terms) >= max_terms:
            break

    if not terms:
        return None

    return " | ".join(terms)


async def hybrid_search_chunk(
    conn: asyncpg.Connection,
    chunk_embedding: list[float],
    chunk_text: str,
    semantic_limit: int = 100,
    bm25_limit: int = 100,
) -> dict[int, float]:
    """Run hybrid search for a single chunk embedding + text.

    Returns dict mapping note_id → RRF fusion score.
    """
    # --- Semantic search ---
    sem_rows = await conn.fetch(
        """
        SELECT note_id, 1.0 - (embedding <=> $1::vector) AS similarity
        FROM anki_notes
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $2
        """,
        chunk_embedding,
        semantic_limit,
    )

    # Build semantic ranking: note_id → rank (0-indexed)
    semantic_ranks: dict[int, int] = {}
    for rank, row in enumerate(sem_rows):
        semantic_ranks[row["note_id"]] = rank

    # --- BM25 search ---
    bm25_ranks: dict[int, int] = {}
    query_str = extract_search_terms(chunk_text)
    if query_str:
        try:
            bm25_rows = await conn.fetch(
                """
                SELECT note_id, ts_rank_cd(textsearch, to_tsquery('english', $1)) AS rank
                FROM anki_notes
                WHERE textsearch @@ to_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
                """,
                query_str,
                bm25_limit,
            )
            for rank, row in enumerate(bm25_rows):
                bm25_ranks[row["note_id"]] = rank
        except Exception:
            # Fall back to semantic-only on tsquery parse errors
            logger.warning("BM25 query failed, falling back to semantic-only", exc_info=True)

    # --- RRF fusion ---
    all_note_ids = set(semantic_ranks.keys()) | set(bm25_ranks.keys())
    rrf_scores: dict[int, float] = {}

    for nid in all_note_ids:
        score = 0.0
        if nid in semantic_ranks:
            score += 1.0 / (_RRF_K + semantic_ranks[nid])
        if nid in bm25_ranks:
            score += 1.0 / (_RRF_K + bm25_ranks[nid])
        rrf_scores[nid] = score

    return rrf_scores
