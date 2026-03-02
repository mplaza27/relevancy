[x]
# Prompt 12B: Local Test Agent

## When to Run
After prompts 01–12 are complete and both servers run locally without errors.

## Goal
Define and run a specialized test agent that systematically validates every layer of the local stack — parser, backend, and frontend — and produces a pass/fail report. No deployment needed; everything runs on `localhost`.

## Agent Definition

Add this to `AGENTS.md`:

```
### Tester-Local
Runs the full local test suite and reports results. Does not write production code — only writes tests and fixes them.

**Trigger**: After prompts 01-12 are complete.
**Tools**: Read, Bash, Write (test files only).
**Context**: Full project. Both servers must be running before invoking.
**Handoff**: Written test report at `tests/local-test-report.md`. All checks must pass before proceeding to prompt 13.
```

## Pre-conditions (Tester-Local must verify these first)
```bash
# 1. Backend is running
curl -sf http://localhost:8000/health || echo "FAIL: backend not running"

# 2. Supabase (or local PG) has anki_notes populated
curl -sf http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['db_connected'], 'DB not connected'"

# 3. Frontend is running
curl -sf http://localhost:5173 || echo "FAIL: frontend not running"

# 4. anki_parser is importable
python3 -c "import anki_parser; print('anki_parser OK')"
```

If any pre-condition fails, the agent stops and reports which one failed.

## Test Suites

### Suite 1 — Anki Parser (run via pytest)
```bash
cd packages/anki_parser && python -m pytest tests/ -v --tb=short 2>&1
```

Expected: All text extraction tests pass. If the full `.apkg` is available, verify note/card counts match.

Specific assertions:
- `strip_cloze("{{c1::mitochondria::hint}}")` → `"mitochondria"`
- `strip_html("<b>Hello</b><br>World")` → `"Hello\nWorld"`
- `extract_image_refs('<img src="heart.jpg">')` → `["heart.jpg"]`
- `is_meaningful_field("")` → `False`
- `is_meaningful_field("<div>   </div>")` → `False`
- `is_meaningful_field("<b>ATP synthesis</b>")` → `True`

### Suite 2 — Backend Unit Tests
```bash
cd backend && python -m pytest tests/ -v --tb=short 2>&1
```

Specific assertions:
- `chunk_text("")` → `[]`
- `chunk_text("short")` → `["short"]`
- All chunks from a 5000-char text are ≤ 900 chars (~225 tokens)
- `extract_text(pdf_fixture)` returns non-empty string
- Sync script template renders with note IDs baked in

### Suite 3 — Backend API (live, via httpx)
```bash
cd backend && python -m pytest tests/test_api.py -v --tb=short 2>&1
```

If `tests/test_api.py` doesn't exist, the agent creates it. Tests:

```python
import pytest
import httpx

BASE = "http://localhost:8000"

def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["model_loaded"] is True
    assert data["db_connected"] is True

def test_upload_invalid_type():
    r = httpx.post(f"{BASE}/api/upload",
        files={"files": ("test.exe", b"fake", "application/octet-stream")})
    assert r.status_code == 400

def test_upload_valid_pdf(sample_pdf_bytes):
    r = httpx.post(f"{BASE}/api/upload",
        files={"files": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["match_count"] >= 0
    return data["session_id"]

def test_get_matches(uploaded_session_id):
    r = httpx.get(f"{BASE}/api/match/{uploaded_session_id}")
    assert r.status_code == 200
    data = r.json()
    assert "cards" in data
    for card in data["cards"]:
        assert 0.0 <= card["similarity"] <= 1.0
        assert "note_id" in card
        assert "text" in card
        assert "tags" in card

def test_sync_script(uploaded_session_id):
    r = httpx.get(f"{BASE}/api/sync/script",
        params={"session_id": uploaded_session_id, "threshold": 0.3})
    assert r.status_code == 200
    assert "text/x-python" in r.headers["content-type"]
    assert "NOTE_IDS" in r.text
    assert "ankiconnect" in r.text.lower()

def test_sync_search_query(uploaded_session_id):
    r = httpx.get(f"{BASE}/api/sync/search-query",
        params={"session_id": uploaded_session_id, "threshold": 0.3})
    assert r.status_code == 200
    data = r.json()
    assert 'deck:"AnKing Step Deck"' in data["query"]
    assert "nid:" in data["query"]
```

### Suite 4 — Relevancy Quality Check
Validates that the matching actually works (not just that it runs):

```python
# Create a PDF with known medical content and verify expected cards appear
CARDIO_TEXT = """
Heart sounds: S1 is closure of mitral and tricuspid valves.
S2 is closure of aortic and pulmonic valves.
Aortic stenosis causes a crescendo-decrescendo systolic murmur.
"""

# Upload this text, get results at threshold=0.2
# Assert: at least 5 cards returned
# Assert: top card similarity > 0.4
# Assert: at least one result has a cardiovascular-related tag
```

### Suite 5 — Sync Script Dry Run
```bash
python backend/tests/fixtures/dry_run_sync_script.py
```

Creates a sync script with a dummy note ID list and runs it with `--dry-run` flag (which the script should support — add a `DRY_RUN = True` flag to the script template that prints actions without calling AnkiConnect).

### Suite 6 — Frontend Smoke Test (curl-based)
```bash
# Frontend serves static files
curl -sf http://localhost:5173 | grep -q "Relevancey" || echo "FAIL: page title missing"

# Check that main JS bundle is served
curl -sf http://localhost:5173 | grep -q 'src="/assets' || echo "FAIL: JS bundle not linked"
```

## Test Report

The agent writes `tests/local-test-report.md`:

```markdown
# Local Test Report
Date: {timestamp}
Backend: http://localhost:8000
Frontend: http://localhost:5173

## Results
| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| Anki Parser | N | N | N |
| Backend Unit | N | N | N |
| Backend API | N | N | N |
| Quality Check | N | N | N |
| Sync Script | N | N | N |
| Frontend Smoke | N | N | N |

## Status: PASS / FAIL

## Failures
(list any failures with error messages)

## Notes
(any warnings or observations)
```

## Pass Criteria
All 6 suites must pass before the project moves to prompt 13. If any suite fails, the agent reports the specific failure and the fix needed — it does NOT proceed to deployment.
