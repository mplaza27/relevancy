[x]
# Prompt 12: Integration & Testing

## Goal
Connect frontend to backend, run end-to-end tests, fix any issues, and polish the full workflow.

## Context
- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:5173` (Vite dev server)
- CORS is configured in backend to allow frontend origin
- Need to test the full flow: upload → match → slider → sync

## Tasks

### 1. End-to-End Workflow Test
Run both servers and test manually:

```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Test sequence:
1. Open `http://localhost:5173`
2. Upload a medical PDF or PPTX
3. Wait for matching to complete (should be < 5 seconds)
4. Verify card results appear
5. Slide the relevancy threshold — card count should update instantly
6. Expand a card — verify Extra, Pathoma, B&B fields display correctly
7. Click "Download Sync Script" — verify .py file downloads with correct note IDs
8. Click "Copy" on search query — paste into a text editor to verify format
9. Click "Download Note ID List" — verify .txt file has correct IDs

### 2. Backend Unit Tests

```bash
cd backend && pip install -e ".[dev]" && pytest
```

Tests to write:
- `tests/test_document_parser.py` — extraction from each file type
- `tests/test_chunker.py` — chunking with various text lengths
- `tests/test_matcher.py` — matching logic (mock DB, verify deduplication and ranking)
- `tests/test_sync.py` — script generation (verify template renders correctly with note IDs)

### 3. Anki Parser Tests

```bash
cd packages/anki_parser && pip install -e ".[dev]" && pytest
```

Tests to write (from prompt 02):
- Text extraction (cloze, HTML, sound refs)
- Full .apkg parsing against real AnKing deck (if available as fixture)

### 4. Common Issues to Check

**CORS:**
- Backend must allow `http://localhost:5173` in development
- Check `Access-Control-Allow-Origin` header in responses

**File upload:**
- Large files (50MB) don't timeout
- Multiple files upload in one request
- Invalid file types are rejected with helpful error

**Embeddings:**
- Model loads at startup (not on first request)
- Embedding is thread-safe (sentence-transformers `encode()` with `asyncio.to_thread`)
- Chunks longer than 256 tokens are handled gracefully (truncated by model)

**Database:**
- Connection pool doesn't exhaust (max 5 connections, Supabase allows ~30 on free tier)
- Session cleanup works (expired sessions are deletable)
- Vector search returns results in reasonable time (< 100ms for 30K vectors)

**Frontend:**
- Loading state is shown during upload and matching
- Error states are handled (backend unreachable, upload fails)
- Slider is responsive with 200+ cards
- Card expansion/collapse works correctly

### 5. Create a test fixture
Create a small test PDF with medical content for automated testing:
```python
# tests/fixtures/create_test_pdf.py
# Generate a small PDF with known medical text for testing
```

Or provide instructions to manually create a test file.

### 6. Dev environment setup script
Create `scripts/dev_setup.sh`:
```bash
#!/bin/bash
# Set up the full development environment

# Install anki_parser
cd packages/anki_parser && pip install -e ".[dev]" && cd ../..

# Install backend
cd backend && pip install -e ".[dev]" && cd ..

# Install frontend
cd frontend && npm install && cd ..

echo "Setup complete. Run:"
echo "  Backend: cd backend && uvicorn app.main:app --reload --port 8000"
echo "  Frontend: cd frontend && npm run dev"
```

## Verification Checklist
- [ ] Upload a PDF → get relevant cards in < 5 seconds
- [ ] Slider changes card count in real-time
- [ ] Expanding a card shows resource fields
- [ ] Tags display with readable formatting
- [ ] Script download works and contains correct note IDs
- [ ] Search query copy works
- [ ] Note ID list download works
- [ ] Backend handles errors gracefully (bad file type, empty file, etc.)
- [ ] All tests pass
