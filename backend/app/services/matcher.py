"""Matching pipeline: hybrid search → aggregation → cross-encoder reranking."""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import asyncpg
import numpy as np

from app.embeddings import cross_encode, is_cross_encoder_loaded
from app.services.search import hybrid_search_chunk

logger = logging.getLogger(__name__)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(x >= 0, 1 / (1 + np.exp(-x)), np.exp(x) / (1 + np.exp(x)))


def _min_max_normalize(scores: list[float]) -> list[float]:
    """Normalize scores to [0, 1] via min-max scaling."""
    if not scores:
        return scores
    lo, hi = min(scores), max(scores)
    if hi == lo:
        return [1.0] * len(scores)
    return [(s - lo) / (hi - lo) for s in scores]


# Max characters fed to cross-encoder per text — keeps sequence length short (BERT is O(n²))
_CE_MAX_CHARS = 400


async def run_matching(
    pool: asyncpg.Pool,
    session_id: UUID,
    chunk_embeddings: np.ndarray,
    chunk_texts: list[str] | None = None,
    semantic_limit_per_chunk: int = 300,
    bm25_limit_per_chunk: int = 200,
    max_results: int = 100,
) -> list[dict]:
    """Match document chunks against Anki notes via hybrid search + reranking.

    Pipeline:
    1. Per chunk: hybrid search (semantic + BM25 with RRF fusion)
    2. Aggregate: keep max RRF score per note across all chunks
    3. Take top 2x max_results candidates by RRF (enough headroom for reranking to reshuffle)
    4. Cross-encoder score those candidates
    5. Sort by cross-encoder score, take top max_results
    6. Min-max normalize only those → 0%–100%
    7. Store results

    Returns list of match dicts sorted by similarity descending.
    """
    # --- 1. Per-chunk hybrid search ---
    aggregated: dict[int, tuple[float, int]] = {}

    async with pool.acquire() as conn:
        for chunk_idx, emb in enumerate(chunk_embeddings):
            chunk_text = chunk_texts[chunk_idx] if chunk_texts else ""
            rrf_scores = await hybrid_search_chunk(
                conn,
                emb.tolist(),
                chunk_text,
                semantic_limit=semantic_limit_per_chunk,
                bm25_limit=bm25_limit_per_chunk,
            )

            for nid, score in rrf_scores.items():
                if nid not in aggregated or score > aggregated[nid][0]:
                    aggregated[nid] = (score, chunk_idx)

    if not aggregated:
        return []

    # --- 2. Sort by RRF, take top candidates for cross-encoder ---
    sorted_candidates = sorted(aggregated.items(), key=lambda x: x[1][0], reverse=True)
    # Cap at max_results + 50 — enough headroom for reranking without scoring too many pairs
    rerank_pool_size = min(len(sorted_candidates), max_results + 50)
    rerank_candidates = sorted_candidates[:rerank_pool_size]
    rerank_nids = [nid for nid, _ in rerank_candidates]

    logger.info(
        "Hybrid search: %d total candidates, cross-encoding top %d",
        len(sorted_candidates), rerank_pool_size,
    )

    # --- 3. Fetch note metadata for rerank pool only ---
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT note_id, notetype, deck, text, extra, tags, raw_fields
            FROM anki_notes
            WHERE note_id = ANY($1::bigint[])
            """,
            rerank_nids,
        )

    note_data: dict[int, dict] = {}
    for row in rows:
        note_data[row["note_id"]] = dict(row)

    # --- 4. Score candidates ---
    raw_scores: dict[int, float] = {}

    if is_cross_encoder_loaded() and chunk_texts:
        pairs: list[tuple[str, str]] = []
        pair_nids: list[int] = []
        for nid, (_, best_chunk_idx) in rerank_candidates:
            if nid not in note_data:
                continue
            nd = note_data[nid]
            note_text = f"{nd['text']} {nd.get('extra', '') or ''}".strip()[:_CE_MAX_CHARS]
            chunk_text = chunk_texts[best_chunk_idx][:_CE_MAX_CHARS]
            pairs.append((chunk_text, note_text))
            pair_nids.append(nid)

        if pairs:
            logger.info("Cross-encoding %d pairs...", len(pairs))
            logits = await asyncio.to_thread(cross_encode, pairs)
            scores = _sigmoid(logits)

            for nid, score in zip(pair_nids, scores):
                raw_scores[nid] = float(score)
    else:
        for nid, (rrf_score, _) in rerank_candidates:
            raw_scores[nid] = rrf_score

    # --- 5. Sort by score, take top max_results ---
    scored_nids = sorted(raw_scores.keys(), key=lambda n: raw_scores[n], reverse=True)
    top_nids = scored_nids[:max_results]

    # --- 6. Min-max normalize only the final set ---
    top_raw = [raw_scores[nid] for nid in top_nids]
    top_normalized = _min_max_normalize(top_raw)

    results = []
    for nid, norm_score in zip(top_nids, top_normalized):
        if nid in note_data:
            note_data[nid]["similarity"] = norm_score
            results.append(note_data[nid])

    logger.info("Returning %d results (normalized 0.0–1.0)", len(results))

    # --- 7. Store in match_results ---
    if results:
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO match_results (session_id, note_id, similarity)
                VALUES ($1, $2, $3)
                """,
                [(session_id, r["note_id"], r["similarity"]) for r in results],
            )

    return results
