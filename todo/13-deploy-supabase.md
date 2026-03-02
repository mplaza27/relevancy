[x]
# Prompt 13: Deployment — Supabase Setup

## Goal
Set up the Supabase project, run the schema, and upload pre-computed embeddings for the AnKing deck.

## Context
- Supabase free tier: 500MB database, pgvector included
- Estimated usage: ~135MB of 500MB
- Direct connection on port 5432 (not the pooler on 6543)
- The embeddings JSONL file was created in prompt 03

## Steps

### 1. Create Supabase Project
1. Go to https://supabase.com and sign up / sign in
2. Create a new project (choose closest region)
3. Note the project credentials:
   - **Project URL**: `https://xxxx.supabase.co`
   - **Direct DB connection string**: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
   - Or truly direct: `postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres`
4. Save the connection string to `.env` files

### 2. Enable pgvector Extension
In the Supabase SQL Editor, or via Dashboard > Database > Extensions:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Run the Schema
Copy the entire contents of `sql/schema.sql` (from prompt 04) into the Supabase SQL Editor and run it.

Verify:
```sql
-- Check tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- Should show: anki_notes, upload_sessions, document_chunks, match_results

-- Check vector column
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'anki_notes' AND column_name = 'embedding';
-- Should show: embedding, USER-DEFINED

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'anki_notes';
-- Should show HNSW index
```

### 4. Upload Pre-computed Embeddings
Run the upload script from prompt 03:
```bash
export DATABASE_URL="postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres"
cd scripts
python upload_to_supabase.py
```

This inserts ~28,660 rows into `anki_notes` with embeddings.

Verify:
```sql
SELECT COUNT(*) FROM anki_notes;
-- Should be ~28,660

SELECT note_id, notetype, LEFT(text, 100) AS text_preview, array_length(tags, 1) as tag_count
FROM anki_notes LIMIT 5;

-- Test vector search
SELECT note_id, text, 1 - (embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)) AS similarity
FROM anki_notes
ORDER BY embedding <=> (SELECT embedding FROM anki_notes LIMIT 1)
LIMIT 5;
```

### 5. Check Storage Usage
```sql
SELECT pg_size_pretty(pg_database_size('postgres')) AS total_size;
-- Should be ~130-150MB
```

In Supabase Dashboard > Database > Database Size, verify you're under 500MB.

### 6. Set Up Keep-Alive (Optional)
Supabase free tier pauses after 7 days of inactivity. If this is a concern:
- The Oracle Cloud backend can run a daily cron job:
  ```bash
  # crontab on Oracle Cloud VM
  0 12 * * * curl -s "https://xxxx.supabase.co/rest/v1/anki_notes?select=count&limit=1" -H "apikey: YOUR_ANON_KEY" > /dev/null
  ```
- Or use a free monitoring service (UptimeRobot) to ping the backend, which in turn queries Supabase

### 7. Update Environment Variables
Backend `.env`:
```
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
```

Frontend `.env`:
```
VITE_API_URL=https://your-backend-domain.com
```

## Verification
- [ ] Supabase project created and accessible
- [ ] pgvector extension enabled
- [ ] All 4 tables exist with correct schemas
- [ ] HNSW index created on anki_notes.embedding
- [ ] ~28,660 rows in anki_notes
- [ ] Vector search returns results
- [ ] Database size < 200MB
- [ ] Backend can connect from local machine
