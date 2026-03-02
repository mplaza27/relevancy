-- Verification queries for Supabase deployment (Prompt 13)
-- Run these in the Supabase SQL Editor after schema + data upload

-- 1. Check all 4 tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: anki_notes, document_chunks, match_results, upload_sessions

-- 2. Verify vector column on anki_notes
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name = 'anki_notes' AND column_name = 'embedding';
-- Expected: embedding | USER-DEFINED | vector

-- 3. Check HNSW index exists
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'anki_notes';
-- Expected: idx_anki_notes_embedding (HNSW with vector_cosine_ops)

-- 4. Verify row count after upload
SELECT COUNT(*) AS note_count FROM anki_notes;
-- Expected: ~28660

-- 5. Spot-check a few rows
SELECT note_id, notetype, LEFT(text, 100) AS text_preview, array_length(tags, 1) AS tag_count
FROM anki_notes
LIMIT 5;

-- 6. Test vector similarity search
SELECT
    note_id,
    LEFT(text, 80) AS text_preview,
    1 - (embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)) AS similarity
FROM anki_notes
ORDER BY embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)
LIMIT 5;
-- Expected: first row similarity = 1.0, rest < 1.0

-- 7. Check database size
SELECT pg_size_pretty(pg_database_size('postgres')) AS total_size;
-- Expected: ~130-150 MB (well under 500 MB free tier limit)
