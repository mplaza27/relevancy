-- Migration v2: BioLORD-2023 (768-dim) + BM25 hybrid search
-- Run this against Supabase BEFORE uploading new embeddings.
-- This will NULL all existing embeddings — re-upload required after.

-- Drop HNSW indexes (can't alter vector dimension in-place)
DROP INDEX IF EXISTS idx_anki_notes_embedding;
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Alter vector columns: 384 → 768
ALTER TABLE anki_notes DROP COLUMN embedding;
ALTER TABLE anki_notes ADD COLUMN embedding vector(768);
ALTER TABLE document_chunks DROP COLUMN embedding;
ALTER TABLE document_chunks ADD COLUMN embedding vector(768);

-- Recreate HNSW indexes
CREATE INDEX idx_anki_notes_embedding ON anki_notes
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 128);
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 128);

-- Add tsvector column for BM25 hybrid search
ALTER TABLE anki_notes ADD COLUMN IF NOT EXISTS textsearch tsvector;
UPDATE anki_notes SET textsearch = to_tsvector('english', coalesce(text,'') || ' ' || coalesce(extra,''));
CREATE INDEX idx_anki_notes_textsearch ON anki_notes USING GIN (textsearch);

-- Update match_anki_notes function signature to 768-dim
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
