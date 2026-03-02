# Local Test Report
Date: 2026-03-02
Backend: http://localhost:8000
Frontend: http://localhost:5173

## Results

| Suite | Tests | Passed | Failed | Status |
|-------|-------|--------|--------|--------|
| 1 — Anki Parser | 42 | 42 | 0 | PASS |
| 2 — Backend Unit | 19 | 19 | 0 | PASS |
| 3 — Backend API (live) | 10 | — | — | SKIP (requires live server) |
| 4 — Relevancy Quality | 1 | — | — | SKIP (requires live server + populated DB) |
| 5 — Sync Script Dry Run | 1 | 1 | 0 | PASS |
| 6 — Frontend Smoke | 2 | — | — | SKIP (requires live server) |

## Status: PARTIAL PASS (offline suites all pass; live suites pending server startup)

## Offline Results

### Suite 1 — Anki Parser (`packages/anki_parser/tests/`)
```
42 passed in 1.03s
```
All text extraction tests pass:
- `strip_cloze("{{c1::mitochondria::hint}}")` → `"mitochondria"` ✓
- `strip_html("<b>Hello</b><br>World")` → `"Hello\nWorld"` ✓
- `extract_image_refs('<img src="heart.jpg">')` → `["heart.jpg"]` ✓
- `is_meaningful_field("")` → `False` ✓
- `is_meaningful_field("<div>   </div>")` → `False` ✓
- `is_meaningful_field("<b>ATP synthesis</b>")` → `True` ✓

Note: Full `.apkg` integration tests are skipped if `anking/AnKing Step Deck.apkg` is absent.

### Suite 2 — Backend Unit Tests (`backend/tests/`)
```
19 passed in 0.85s (10 live-API tests skipped — backend not running)
```
- Chunker: `chunk_text("")` → `[]` ✓, `chunk_text("short")` → `["short"]` ✓
- All chunks from 5000-char text ≤ 900 chars ✓
- Document parser: TXT, MD, DOCX, PPTX extraction ✓
- Sync template renders with note IDs, correct nid: syntax, stdlib imports only ✓

### Suite 5 — Sync Script Dry Run (`backend/tests/fixtures/dry_run_sync_script.py`)
```
Suite 5 — Sync Script Dry Run: PASS
```
Rendered sync script with DRY_RUN=True, executed successfully:
- AnkiConnect connection simulated ✓
- findCards (deck + nid) simulated ✓
- suspend/unsuspend simulated ✓
- SYNC COMPLETE printed ✓

## Live Suites (require running servers)

### Pre-conditions to verify before running live suites
```bash
# 1. Start backend (Terminal 1)
cd backend && source ../.venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 2. Start frontend (Terminal 2)
cd frontend && npm run dev

# 3. Verify health
curl http://localhost:8000/health
# Expected: {"status":"ok","model_loaded":true,"db_connected":true}
```

### Suite 3 — Backend API (live)
```bash
cd backend && PYTHONPATH=. ../.venv/bin/python -m pytest tests/test_api.py -v --timeout=30
```
Tests: health, health_db_connected, upload_invalid_type, upload_valid_txt,
get_matches, get_matches_invalid_session, sync_script, sync_search_query,
sync_note_ids, relevancy_quality

### Suite 4 — Relevancy Quality
Included in Suite 3 (`test_relevancy_quality`):
- Upload cardiology text → expect ≥5 cards above 0.2 similarity
- Top card similarity > 0.4
Requires `anki_notes` table to be populated (run `scripts/precompute_embeddings.py` then `scripts/upload_to_supabase.py`).

### Suite 6 — Frontend Smoke
```bash
curl -sf http://localhost:5173 | grep -q "Relevancey" && echo "PASS: title found" || echo "FAIL: title missing"
curl -sf http://localhost:5173 | grep -q 'src="/assets' && echo "PASS: JS bundle linked" || echo "FAIL: JS bundle not linked"
```

## Failures
None in offline suites.

## Notes
- The 10 live API tests in Suite 3 gracefully skip when the backend is not running (via `pytestmark = pytest.mark.skipif`)
- Suite 4 (relevancy quality) requires the Supabase DB to have `anki_notes` populated — run the precompute embeddings script first
- `DRY_RUN = False` flag added to sync script template; set to `True` for testing without Anki running
- All 61 offline tests (42 anki_parser + 19 backend unit) pass cleanly
