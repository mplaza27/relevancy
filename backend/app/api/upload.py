from __future__ import annotations

import asyncio
import logging
import tempfile
from collections import Counter
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile

from app.config import settings
from app.limiter import limiter
from app.database import get_db, get_pool
from app.embeddings import embed_texts
from app.services.chunker import chunk_text
from app.services.document_parser import SUPPORTED_EXTENSIONS, extract_text
from app.services.matcher import run_matching
from app.services.search import extract_search_terms

logger = logging.getLogger(__name__)

router = APIRouter()


async def _save_to_temp(file: UploadFile) -> Path:
    """Stream an UploadFile to a temp file. Returns temp path."""
    suffix = Path(file.filename or "upload").suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        chunk_size = 64 * 1024  # 64KB chunks
        total = 0
        while True:
            data = await file.read(chunk_size)
            if not data:
                break
            total += len(data)
            if total > settings.max_upload_size:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    413,
                    f"File {file.filename!r} exceeds max size "
                    f"({settings.max_upload_size // 1024 // 1024}MB)",
                )
            tmp.write(data)
    return tmp_path


async def _process_in_background(
    pool,
    session_id: UUID,
    all_chunk_records: list[dict],
    max_results: int,
) -> None:
    """Embed chunks, run matching, and store results. Updates session status when done."""
    try:
        texts = [r["text"] for r in all_chunk_records]
        embeddings = await asyncio.to_thread(embed_texts, texts)

        # Store chunks in DB
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO document_chunks (session_id, filename, chunk_index, text, embedding)
                VALUES ($1, $2, $3, $4, $5::vector)
                """,
                [
                    (
                        r["session_id"],
                        r["filename"],
                        r["chunk_index"],
                        r["text"],
                        embeddings[i].tolist(),
                    )
                    for i, r in enumerate(all_chunk_records)
                ],
            )

        # Run matching (semantic + BM25 + optional cross-encoder reranking)
        await run_matching(
            pool, session_id, embeddings, chunk_texts=texts, max_results=max_results,
        )

        # Delete user document chunks — only match results are needed from here
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM document_chunks WHERE session_id=$1",
                session_id,
            )

        # Mark session as done
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE upload_sessions SET status='done' WHERE id=$1",
                session_id,
            )

    except Exception as exc:
        logger.exception("Background processing failed for session %s", session_id)
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE upload_sessions SET status='error' WHERE id=$1",
                    session_id,
                )
        except Exception:
            pass


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_and_match(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    max_results: int = Query(default=100, ge=1, le=2000),
) -> dict:
    """Upload one or more documents and start async matching against Anki notes.

    Returns immediately with session_id and status 'processing'.
    Poll GET /api/match/{session_id} until status is 'done'.
    """
    pool = get_pool()

    if not files:
        raise HTTPException(400, "No files provided")
    if len(files) > settings.max_files_per_session:
        raise HTTPException(400, f"Max {settings.max_files_per_session} files per upload")

    # Validate file types
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                400,
                f"Unsupported file type: {suffix!r}. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}",
            )

    session_id = uuid4()

    # Save files to temp and extract text+chunks (must happen in request context
    # before response is sent, since UploadFile objects are tied to the request).
    all_chunk_records: list[dict] = []
    for file in files:
        temp_path = await _save_to_temp(file)
        try:
            text = await asyncio.to_thread(extract_text, temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

        chunks = chunk_text(text)
        for i, chunk_text_str in enumerate(chunks):
            all_chunk_records.append({
                "session_id": session_id,
                "filename": file.filename or "unknown",
                "chunk_index": i,
                "text": chunk_text_str,
            })

    if not all_chunk_records:
        raise HTTPException(422, "No text could be extracted from the uploaded files")

    # Extract keywords from document text (fast — no ML)
    texts = [r["text"] for r in all_chunk_records]
    word_counts: Counter[str] = Counter()
    for t in texts:
        terms_str = extract_search_terms(t, max_terms=50)
        if terms_str:
            for term in terms_str.split(" | "):
                word_counts[term] += 1
    keywords = [w for w, _ in word_counts.most_common(30)]

    # Create session record with keywords
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO upload_sessions (id, file_count, status, keywords)
            VALUES ($1, $2, 'processing', $3)
            """,
            session_id,
            len(files),
            keywords,
        )

    # Schedule heavy work (embed + match + rerank) as a background task
    background_tasks.add_task(
        _process_in_background, pool, session_id, all_chunk_records, max_results
    )

    return {
        "session_id": str(session_id),
        "keywords": keywords,
        "status": "processing",
    }
