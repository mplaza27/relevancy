[x]
# Prompt 03: Pre-compute Embeddings Script

## Goal
Create a script that runs locally on the 3080 FE GPU to generate embeddings for all 28,660 Anki notes and output them as a file that can be uploaded to Supabase.

## Context
- Run on local machine with NVIDIA 3080 FE (10GB VRAM)
- Model: `all-MiniLM-L6-v2` (80MB, 384-dim output, max 256 tokens)
- 28,660 notes to embed — should take seconds on GPU
- Output: JSON or CSV file with (note_id, embedding_vector, metadata) that the Supabase upload script can consume
- Depends on `anki_parser` package from prompt 02

## File: `scripts/precompute_embeddings.py`

### Implementation

```python
#!/usr/bin/env python3
"""
Pre-compute embeddings for all Anki notes.
Run locally on GPU: python scripts/precompute_embeddings.py

Outputs: scripts/output/embeddings.jsonl
"""
```

### Steps the script should perform:

1. **Parse the Anki deck**
   ```python
   from anki_parser import parse_apkg, extract_clean_text
   collection = parse_apkg("anking/AnKing Step Deck.apkg")
   ```

2. **Prepare text for each note**
   - For `AnKingOverhaul` notes: combine `Text` + `Extra` fields (cleaned)
   - For `IO-one by one` notes: combine `Header` + `Extra` fields (cleaned)
   - Include tag text as additional context (flatten hierarchical tags)
   - Skip notes where all fields are empty after cleaning
   - Truncate to ~900 characters (~225 tokens, safe for 256-token limit)

   ```python
   def prepare_note_text(note, notetype_name):
       if notetype_name == "AnKingOverhaul":
           text = note.get_clean_field("Text")
           extra = note.get_clean_field("Extra")
           combined = f"{text} {extra}".strip()
       elif notetype_name == "IO-one by one":
           header = note.get_clean_field("Header")
           extra = note.get_clean_field("Extra")
           combined = f"{header} {extra}".strip()
       else:
           # Generic: combine all fields
           combined = " ".join(
               note.get_clean_field(f) for f in note.field_values
           ).strip()

       # Add flattened tags as context
       tag_text = " ".join(
           t.replace("#", "").replace("::", " ")
           for t in note.tags[:5]  # limit to avoid overwhelming
       )
       if tag_text:
           combined = f"{combined} [{tag_text}]"

       return combined[:900]  # safe for 256-token limit
   ```

3. **Generate embeddings in batches**
   ```python
   from sentence_transformers import SentenceTransformer

   model = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")

   # Batch encode all texts
   embeddings = model.encode(
       texts,
       batch_size=256,  # GPU can handle large batches
       show_progress_bar=True,
       normalize_embeddings=True,  # Pre-normalize for cosine similarity
   )
   ```

4. **Output as JSONL** (one JSON object per line)
   ```jsonl
   {"note_id": 1368291917470, "text": "cleaned text...", "tags": ["tag1", "tag2"], "notetype": "AnKingOverhaul", "embedding": [0.123, -0.456, ...]}
   ```

5. **Also create a Supabase upload script** (`scripts/upload_to_supabase.py`)
   - Read the JSONL file
   - Connect to Supabase PostgreSQL directly via `psycopg` (sync, simpler for one-off script)
   - Batch insert into the `anki_notes` table
   - Use `COPY` or `executemany` for speed
   - Print progress

### Output directory
```
scripts/
├── precompute_embeddings.py     # Generate embeddings
├── upload_to_supabase.py        # Upload to Supabase
└── output/
    └── embeddings.jsonl         # Intermediate output (gitignored)
```

### Dependencies for scripts
Add a `scripts/requirements.txt`:
```
sentence-transformers>=3.0
torch>=2.0
psycopg[binary]>=3.1
pgvector>=0.3
anki-parser @ file:../packages/anki_parser
```

## Verification
- Script completes in < 60 seconds on GPU
- Output file has 28,660 lines (one per note, excluding empty notes)
- Each line has a 384-element embedding vector
- Embeddings are normalized (L2 norm ≈ 1.0)
- Upload script successfully inserts all rows into Supabase

## Notes
- The output JSONL file will be ~200-300MB — add `scripts/output/` to `.gitignore`
- The upload script needs `DATABASE_URL` environment variable pointing to Supabase direct connection (port 5432)
- Consider adding a `--dry-run` flag to preview without writing
- Consider adding a `--sample N` flag to process only N notes for testing
