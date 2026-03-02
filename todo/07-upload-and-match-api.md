[x]
# Prompt 07: Upload & Match API

## Goal
Implement the file upload endpoint and the vector similarity matching endpoint. This is the core business logic — upload a document, embed it, search against Anki notes, return ranked results.

## Context
- Location: `backend/app/api/upload.py`, `backend/app/api/match.py`, `backend/app/services/matcher.py`
- Depends on: database pool (prompt 05), embedding service (prompt 05), document parser (prompt 06)
- Upload flow: receive file → save to temp → extract text → chunk → embed → store chunks → match → return results
- Anonymous sessions identified by UUID

## Files to Implement

### 1. `backend/app/api/upload.py` — File upload endpoint

**`POST /api/upload`** — Accept multipart file upload(s)
- Accept 1-5 files per request
- Validate file types: `.pdf`, `.pptx`, `.docx`, `.txt`, `.md`
- Validate file size: max 50MB each
- Stream to temp file (don't buffer entire file in memory)
- Create an `upload_session` row in DB
- For each file:
  1. Extract text with `document_parser.extract_text()`
  2. Chunk text with `chunker.chunk_text()`
  3. Embed all chunks with `embeddings.embed_texts()` (via `asyncio.to_thread`)
  4. Insert chunks + embeddings into `document_chunks` table
- Run matching (see below)
- Clean up temp files in `finally` block
- Return `{ session_id, file_count, total_chunks, status }`

```python
@router.post("/api/upload")
async def upload_and_match(
    files: list[UploadFile] = File(...),
    pool = Depends(get_pool),
):
    # Validate
    if len(files) > settings.max_files_per_session:
        raise HTTPException(400, f"Max {settings.max_files_per_session} files")

    # Create session
    session_id = uuid4()
    # ... insert upload_sessions row

    # Process each file
    all_chunks = []
    for file in files:
        temp_path = await save_to_temp(file)
        try:
            text = await asyncio.to_thread(extract_text, temp_path)
            chunks = chunk_text(text)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "session_id": session_id,
                    "filename": file.filename,
                    "chunk_index": i,
                    "text": chunk,
                })
        finally:
            cleanup_temp(temp_path)

    # Embed all chunks at once (batched)
    texts = [c["text"] for c in all_chunks]
    embeddings = await asyncio.to_thread(embed_texts, texts)

    # Store chunks + embeddings in DB
    # ... batch insert into document_chunks

    # Run matching
    results = await run_matching(pool, session_id, embeddings)

    return {
        "session_id": str(session_id),
        "file_count": len(files),
        "total_chunks": len(all_chunks),
        "match_count": len(results),
        "status": "done",
    }
```

### 2. `backend/app/services/matcher.py` — Matching logic

**Core algorithm:**
1. For each document chunk embedding, query pgvector for top-K similar Anki notes
2. Aggregate results across all chunks (same note may match multiple chunks)
3. For duplicate notes, keep the highest similarity score
4. Return deduplicated, sorted results

```python
async def run_matching(
    pool: asyncpg.Pool,
    session_id: UUID,
    chunk_embeddings: np.ndarray,
    match_limit_per_chunk: int = 50,
) -> list[dict]:
    """Match document chunks against Anki notes."""

    async with pool.acquire() as conn:
        all_matches = {}  # note_id -> best match dict

        for i, emb in enumerate(chunk_embeddings):
            # Query pgvector
            rows = await conn.fetch(
                """
                SELECT note_id, notetype, deck, text, extra, tags, raw_fields,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM anki_notes
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                emb,
                match_limit_per_chunk,
            )

            for row in rows:
                nid = row["note_id"]
                sim = float(row["similarity"])
                if nid not in all_matches or sim > all_matches[nid]["similarity"]:
                    all_matches[nid] = dict(row)

        # Sort by similarity descending
        results = sorted(all_matches.values(), key=lambda x: x["similarity"], reverse=True)

        # Store in match_results table
        await conn.executemany(
            """INSERT INTO match_results (session_id, note_id, similarity)
               VALUES ($1, $2, $3)""",
            [(session_id, r["note_id"], r["similarity"]) for r in results],
        )

    return results
```

### 3. `backend/app/api/match.py` — Results retrieval endpoint

**`GET /api/match/{session_id}`** — Retrieve cached match results
- Fetch from `match_results` joined with `anki_notes`
- Return all matches (frontend filters by threshold)
- Include all fields the frontend needs for display

```python
@router.get("/api/match/{session_id}")
async def get_matches(session_id: str, pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.note_id, m.similarity,
                   n.notetype, n.text, n.extra, n.tags, n.raw_fields
            FROM match_results m
            JOIN anki_notes n ON m.note_id = n.note_id
            WHERE m.session_id = $1
            ORDER BY m.similarity DESC
            """,
            UUID(session_id),
        )

    return {
        "session_id": session_id,
        "cards": [
            {
                "note_id": row["note_id"],
                "text": row["text"],
                "extra": row["extra"],
                "tags": row["tags"],
                "notetype": row["notetype"],
                "similarity": round(row["similarity"], 4),
                "raw_fields": row["raw_fields"],  # JSONB → dict
            }
            for row in rows
        ],
    }
```

### 4. Register routers in `main.py`
```python
from app.api.upload import router as upload_router
from app.api.match import router as match_router

app.include_router(upload_router)
app.include_router(match_router)
```

## Performance Notes
- Embedding 20 chunks on CPU: ~0.5-1 second
- 20 pgvector queries (top-50 each): ~20-100ms total with HNSW index
- Total response time for a typical lecture PDF: **1-3 seconds**
- The `match_limit_per_chunk=50` × 20 chunks = up to 1000 candidate matches, deduplicated to typically 100-300 unique notes

## Verification
```bash
# Start the server
cd backend && uvicorn app.main:app --reload --port 8000

# Upload a test PDF
curl -X POST http://localhost:8000/api/upload \
  -F "files=@test_lecture.pdf" \
  | jq .

# Get results
curl http://localhost:8000/api/match/{session_id} | jq '.cards[:3]'
```

Expected response shape:
```json
{
  "session_id": "abc-123",
  "cards": [
    {
      "note_id": 1368291917470,
      "text": "Single S1 S2",
      "extra": "Normal heart sounds...",
      "tags": ["#AK_Step1_v12::...", "..."],
      "notetype": "AnKingOverhaul",
      "similarity": 0.8234,
      "raw_fields": {"Pathoma": "...", "Boards and Beyond": "..."}
    }
  ]
}
```
