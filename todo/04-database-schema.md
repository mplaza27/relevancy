[x]
# Prompt 04: Database Schema & Supabase Setup

## Goal
Define the PostgreSQL schema with pgvector for storing Anki note embeddings and user upload sessions. Create the SQL migration file.

## Context
- Database: Supabase free tier (500MB, pgvector included)
- Vector dimensions: 384 (from `all-MiniLM-L6-v2`)
- ~28,660 notes with embeddings (~44MB vectors + ~50MB metadata = ~124MB total)
- Index: HNSW for cosine similarity
- No auth — sessions are anonymous, identified by UUID

## File: `sql/schema.sql`

### Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Anki Notes (pre-loaded with embeddings)
-- ============================================
CREATE TABLE anki_notes (
    note_id     BIGINT PRIMARY KEY,           -- Anki note ID
    guid        TEXT NOT NULL,                 -- Anki GUID
    notetype    TEXT NOT NULL,                 -- e.g., "AnKingOverhaul", "IO-one by one"
    deck        TEXT NOT NULL DEFAULT 'AnKing Step Deck',
    text        TEXT NOT NULL,                 -- Cleaned text used for embedding
    extra       TEXT DEFAULT '',               -- Extra field content (cleaned)
    tags        TEXT[] DEFAULT '{}',           -- Array of tag strings
    raw_fields  JSONB DEFAULT '{}',           -- All original field values (for display)
    embedding   vector(384) NOT NULL,          -- Pre-computed embedding
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX idx_anki_notes_embedding
    ON anki_notes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);

-- B-tree indexes for filtered queries
CREATE INDEX idx_anki_notes_notetype ON anki_notes (notetype);
CREATE INDEX idx_anki_notes_tags ON anki_notes USING GIN (tags);
CREATE INDEX idx_anki_notes_deck ON anki_notes (deck);

-- ============================================
-- Upload Sessions (anonymous, ephemeral)
-- ============================================
CREATE TABLE upload_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
    file_count  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'pending'  -- pending, processing, done, error
);

-- ============================================
-- Document Chunks (from uploaded files)
-- ============================================
CREATE TABLE document_chunks (
    id          BIGSERIAL PRIMARY KEY,
    session_id  UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    embedding   vector(384) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_session ON document_chunks (session_id);
CREATE INDEX idx_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- ============================================
-- Match Results (cached per session)
-- ============================================
CREATE TABLE match_results (
    id          BIGSERIAL PRIMARY KEY,
    session_id  UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    note_id     BIGINT NOT NULL REFERENCES anki_notes(note_id),
    similarity  FLOAT NOT NULL,
    matched_chunk_id BIGINT REFERENCES document_chunks(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_matches_session ON match_results (session_id);
CREATE INDEX idx_matches_similarity ON match_results (session_id, similarity DESC);

-- ============================================
-- Cleanup: auto-delete expired sessions
-- ============================================
-- Supabase can run this via pg_cron or the backend can clean up on request
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM upload_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Similarity Search Function
-- ============================================
CREATE OR REPLACE FUNCTION match_anki_notes(
    query_embedding vector(384),
    match_count INT DEFAULT 100,
    match_threshold FLOAT DEFAULT 0.0,
    filter_notetype TEXT DEFAULT NULL,
    filter_deck TEXT DEFAULT NULL
)
RETURNS TABLE (
    note_id BIGINT,
    notetype TEXT,
    deck TEXT,
    text TEXT,
    extra TEXT,
    tags TEXT[],
    raw_fields JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.note_id,
        n.notetype,
        n.deck,
        n.text,
        n.extra,
        n.tags,
        n.raw_fields,
        1 - (n.embedding <=> query_embedding) AS similarity
    FROM anki_notes n
    WHERE
        (filter_notetype IS NULL OR n.notetype = filter_notetype)
        AND (filter_deck IS NULL OR n.deck = filter_deck)
        AND 1 - (n.embedding <=> query_embedding) > match_threshold
    ORDER BY n.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Storage Budget

| Table | Estimated Size |
|-------|---------------|
| anki_notes (28,660 rows × 384-dim vectors) | ~44MB vectors + ~50MB metadata |
| HNSW index | ~30MB |
| document_chunks (ephemeral, cleaned up) | ~5-10MB peak |
| match_results (ephemeral) | ~1-2MB peak |
| Other indexes | ~5MB |
| **Total** | **~135MB / 500MB limit** |

## Setup Instructions (for prompt 13)
1. Create Supabase project at https://supabase.com
2. Go to SQL Editor
3. Run `sql/schema.sql`
4. Note the direct connection string (port 5432) for the backend
5. Run the upload script from prompt 03 to populate `anki_notes`

## Verification
- All tables created without errors
- `\d anki_notes` shows vector(384) column
- `SELECT * FROM match_anki_notes(ARRAY[0.1, 0.2, ...]::vector, 5)` returns results after data is loaded
- HNSW index is used (check with `EXPLAIN ANALYZE`)
