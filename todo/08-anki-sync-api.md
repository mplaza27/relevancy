[x]
# Prompt 08: Anki Sync API

## Goal
Implement the backend endpoints that generate AnkiConnect helper scripts, search queries, and card ID lists for syncing matched cards to the user's local Anki.

## Context
- Location: `backend/app/api/sync.py`
- AnkiConnect exposes REST API on `localhost:8765` on user's machine
- `suspend`/`unsuspend` actions require **card IDs**, but our DB stores **note IDs**
- The helper script converts note IDs → card IDs via AnkiConnect's `findCards` with `nid:` query
- Comma-separated `nid:123,456,789` is the correct Anki search syntax for multiple note IDs
- Script must use only stdlib (`urllib.request`, `json`) — zero dependencies

## Endpoints to Implement

### 1. `GET /api/sync/script?session_id={id}&threshold={float}`
Returns a downloadable `.py` file with matched note IDs baked in.

**Response**: `Content-Type: text/x-python`, `Content-Disposition: attachment; filename=sync_relevancey.py`

The script should:
1. Connect to AnkiConnect on `localhost:8765`
2. Verify connection with `version` action
3. Find ALL card IDs in `deck:"AnKing Step Deck"` via `findCards`
4. Convert note IDs → card IDs via `findCards` with `nid:` query (batch in groups of 500)
5. `suspend` all cards in the deck
6. `unsuspend` only the matched cards
7. Print summary: X cards unsuspended, Y cards suspended

The script template:
```python
SCRIPT_TEMPLATE = '''#!/usr/bin/env python3
"""
Relevancey Anki Sync Script
Generated: {timestamp}

Prerequisites: Anki running + AnkiConnect add-on (code: 2055492159)
Usage: python sync_relevancey.py
"""
import json, sys, urllib.request

ANKICONNECT_URL = "http://localhost:8765"
DECK_NAME = "{deck_name}"
NOTE_IDS = {note_ids}

def invoke(action, **params):
    payload = json.dumps({{"action": action, "version": 6, "params": params}}).encode("utf-8")
    try:
        req = urllib.request.Request(ANKICONNECT_URL, data=payload)
        req.add_header("Content-Type", "application/json")
        response = urllib.request.urlopen(req, timeout=30)
        result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        print("ERROR: Cannot connect to AnkiConnect. Is Anki running?")
        print("Install AnkiConnect: Tools > Add-ons > Get Add-ons > Code: 2055492159")
        sys.exit(1)
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect error: {{result['error']}}")
    return result.get("result")

def main():
    print("Connecting to AnkiConnect...")
    version = invoke("version")
    print(f"  Connected (v{{version}})")

    print(f"\\nFinding all cards in '{{DECK_NAME}}'...")
    all_cards = invoke("findCards", query=f'deck:"{{DECK_NAME}}"')
    if not all_cards:
        print(f"ERROR: Deck '{{DECK_NAME}}' not found or empty.")
        sys.exit(1)
    print(f"  Found {{len(all_cards)}} total cards")

    print(f"\\nLooking up {{len(NOTE_IDS)}} matched notes...")
    matched = []
    for i in range(0, len(NOTE_IDS), 500):
        batch = NOTE_IDS[i:i+500]
        q = "nid:" + ",".join(str(n) for n in batch)
        matched.extend(invoke("findCards", query=q))
    if not matched:
        print("WARNING: No cards found for the given note IDs.")
        sys.exit(1)
    print(f"  Found {{len(matched)}} cards to unsuspend")

    print(f"\\nSuspending all {{len(all_cards)}} cards in '{{DECK_NAME}}'...")
    invoke("suspend", cards=all_cards)
    print("  Done")

    print(f"Unsuspending {{len(matched)}} relevant cards...")
    invoke("unsuspend", cards=matched)
    print("  Done")

    suspended = len(all_cards) - len(matched)
    print(f"\\n{{'=' * 50}}")
    print(f"  SYNC COMPLETE")
    print(f"  {{len(matched)}} cards UNSUSPENDED (ready to study)")
    print(f"  {{suspended}} cards remain suspended")
    print(f"{{'=' * 50}}")

if __name__ == "__main__":
    main()
'''
```

Implementation:
```python
@router.get("/api/sync/script")
async def download_sync_script(
    session_id: str = Query(...),
    threshold: float = Query(default=0.3),
    pool = Depends(get_pool),
):
    # Fetch note IDs above threshold from match_results
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT note_id FROM match_results WHERE session_id = $1 AND similarity >= $2",
            UUID(session_id), threshold,
        )
    note_ids = [row["note_id"] for row in rows]

    script = SCRIPT_TEMPLATE.format(
        timestamp=datetime.utcnow().isoformat(),
        deck_name="AnKing Step Deck",
        note_ids=repr(note_ids),
    )

    return Response(
        content=script,
        media_type="text/x-python",
        headers={"Content-Disposition": "attachment; filename=sync_relevancey.py"},
    )
```

### 2. `GET /api/sync/search-query?session_id={id}&threshold={float}`
Returns the Anki browser search query string.

```python
@router.get("/api/sync/search-query")
async def get_search_query(
    session_id: str = Query(...),
    threshold: float = Query(default=0.3),
    pool = Depends(get_pool),
):
    # Fetch note IDs above threshold
    note_ids = await _get_filtered_note_ids(pool, session_id, threshold)

    # Build Anki search query (comma-separated nid: format)
    query = f'deck:"AnKing Step Deck" nid:{",".join(str(n) for n in note_ids)}'

    return {"query": query, "note_count": len(note_ids)}
```

### 3. `GET /api/sync/note-ids?session_id={id}&threshold={float}`
Returns a downloadable `.txt` file with one note ID per line.

```python
@router.get("/api/sync/note-ids")
async def download_note_ids(
    session_id: str = Query(...),
    threshold: float = Query(default=0.3),
    pool = Depends(get_pool),
):
    note_ids = await _get_filtered_note_ids(pool, session_id, threshold)
    content = "\n".join(str(nid) for nid in note_ids)

    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=relevancey_note_ids.txt"},
    )
```

### 4. Shared helper
```python
async def _get_filtered_note_ids(pool, session_id: str, threshold: float) -> list[int]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT note_id FROM match_results
               WHERE session_id = $1 AND similarity >= $2
               ORDER BY similarity DESC""",
            UUID(session_id), threshold,
        )
    return [row["note_id"] for row in rows]
```

### 5. Register router in `main.py`
```python
from app.api.sync import router as sync_router
app.include_router(sync_router)
```

## Verification
```bash
# Download script
curl "http://localhost:8000/api/sync/script?session_id=abc-123&threshold=0.3" -o sync_test.py
python sync_test.py  # Should fail gracefully if Anki not running

# Get search query
curl "http://localhost:8000/api/sync/search-query?session_id=abc-123&threshold=0.3" | jq .

# Download note ID list
curl "http://localhost:8000/api/sync/note-ids?session_id=abc-123&threshold=0.3" -o ids.txt
wc -l ids.txt
```
