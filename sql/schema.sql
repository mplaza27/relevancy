-- Relevancey — Supabase Schema
-- Run this in the Supabase SQL Editor to initialize the database.
-- Requires: pgvector extension (included in Supabase free tier)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Anki Notes (pre-loaded with embeddings)
-- ============================================
CREATE TABLE anki_notes (
    note_id     BIGINT PRIMARY KEY,                    -- Anki note ID
    guid        TEXT NOT NULL DEFAULT '',              -- Anki GUID
    notetype    TEXT NOT NULL,                         -- e.g., "AnKingOverhaul", "IO-one by one"
    deck        TEXT NOT NULL DEFAULT 'AnKing Step Deck',
    text        TEXT NOT NULL,                         -- Cleaned text used for embedding
    extra       TEXT DEFAULT '',                       -- Extra field content (cleaned)
    tags        TEXT[] DEFAULT '{}',                   -- Array of tag strings
    raw_fields  JSONB DEFAULT '{}',                    -- All original field values (for display)
    embedding   vector(768) NOT NULL,                  -- Pre-computed embedding (BioLORD-2023)
    textsearch  tsvector,                              -- BM25 full-text search
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
-- m=16, ef_construction=128 provides good recall/speed balance
CREATE INDEX idx_anki_notes_embedding
    ON anki_notes USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- GIN index for BM25 full-text search
CREATE INDEX idx_anki_notes_textsearch ON anki_notes USING GIN (textsearch);

-- B-tree indexes for filtered queries
CREATE INDEX idx_anki_notes_notetype ON anki_notes (notetype);
CREATE INDEX idx_anki_notes_deck ON anki_notes (deck);

-- GIN index for tag array queries (e.g., WHERE tags @> ARRAY['Cardiology'])
CREATE INDEX idx_anki_notes_tags ON anki_notes USING GIN (tags);

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
    embedding   vector(768) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_session ON document_chunks (session_id);
CREATE INDEX idx_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- ============================================
-- Match Results (cached per session)
-- ============================================
CREATE TABLE match_results (
    id               BIGSERIAL PRIMARY KEY,
    session_id       UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    note_id          BIGINT NOT NULL REFERENCES anki_notes(note_id),
    similarity       FLOAT NOT NULL,
    matched_chunk_id BIGINT REFERENCES document_chunks(id),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_matches_session ON match_results (session_id);
CREATE INDEX idx_matches_similarity ON match_results (session_id, similarity DESC);

-- ============================================
-- Cleanup: auto-delete expired sessions
-- ============================================
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
-- Returns Anki notes most similar to a query embedding, with optional filters.
-- Uses cosine distance: similarity = 1 - cosine_distance
-- Embeddings must be pre-normalized (L2 norm = 1.0) for correct results.
CREATE OR REPLACE FUNCTION match_anki_notes(
    query_embedding  vector(768),
    match_count      INT DEFAULT 100,
    match_threshold  FLOAT DEFAULT 0.0,
    filter_notetype  TEXT DEFAULT NULL,
    filter_deck      TEXT DEFAULT NULL
)
RETURNS TABLE (
    note_id     BIGINT,
    notetype    TEXT,
    deck        TEXT,
    text        TEXT,
    extra       TEXT,
    tags        TEXT[],
    raw_fields  JSONB,
    similarity  FLOAT
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
        1.0 - (n.embedding <=> query_embedding) AS similarity
    FROM anki_notes n
    WHERE
        (filter_notetype IS NULL OR n.notetype = filter_notetype)
        AND (filter_deck IS NULL OR n.deck = filter_deck)
        AND 1.0 - (n.embedding <=> query_embedding) > match_threshold
    ORDER BY n.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
