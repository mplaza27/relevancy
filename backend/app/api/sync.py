from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.database import get_pool

router = APIRouter()

_DECK_NAME = "AnKing Step Deck"

SCRIPT_TEMPLATE = '''\
#!/usr/bin/env python3
"""
Relevancy Anki Sync Script
Generated: {timestamp}

Prerequisites:
  - Anki must be running
  - AnkiConnect add-on installed (code: 2055492159)
    Tools > Add-ons > Get Add-ons > Code: 2055492159

Usage:
    python sync_relevancy.py

What this does:
  1. Finds all cards in the deck
  2. Suspends all of them
  3. Unsuspends only the cards matched to your uploaded material

Relevancy threshold used: {threshold}
Matched notes: {note_count}
"""
import json
import sys
import urllib.request
import urllib.error

ANKICONNECT_URL = "http://localhost:8765"
DECK_NAME = "{deck_name}"
NOTE_IDS = {note_ids}
DRY_RUN = False  # Set to True to test without a running Anki instance


def invoke(action, **params):
    payload = json.dumps({{"action": action, "version": 6, "params": params}}).encode("utf-8")
    if DRY_RUN:
        print(f"  [DRY RUN] {{action}}")
        if action == "version":
            return 6
        if action == "findCards":
            return [111111111, 222222222]
        return None
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
        raise RuntimeError(f"AnkiConnect error: {{result[\'error\']}}")
    return result.get("result")


def main():
    print("Connecting to AnkiConnect...")
    version = invoke("version")
    print(f"  Connected (v{{version}})")

    print(f"\\nFinding all cards in \'{{DECK_NAME}}\'...")
    all_cards = invoke("findCards", query=f\'deck:"{{DECK_NAME}}"\')
    if not all_cards:
        print(f"ERROR: Deck \'{{DECK_NAME}}\' not found or empty.")
        print("Make sure the AnKing Step Deck is installed in Anki.")
        sys.exit(1)
    print(f"  Found {{len(all_cards)}} total cards")

    print(f"\\nLooking up {{len(NOTE_IDS)}} matched notes...")
    matched = []
    for i in range(0, len(NOTE_IDS), 500):
        batch = NOTE_IDS[i:i + 500]
        q = "nid:" + ",".join(str(n) for n in batch)
        cards = invoke("findCards", query=q)
        if cards:
            matched.extend(cards)
    if not matched:
        print("WARNING: No cards found for the given note IDs.")
        print("This may mean the deck version has changed or cards were deleted.")
        sys.exit(1)
    print(f"  Found {{len(matched)}} cards to unsuspend")

    print(f"\\nSuspending all {{len(all_cards)}} cards in \'{{DECK_NAME}}\'...")
    invoke("suspend", cards=all_cards)
    print("  Done")

    print(f"Unsuspending {{len(matched)}} relevant cards...")
    invoke("unsuspend", cards=matched)
    print("  Done")

    suspended = len(all_cards) - len(matched)
    sep = "=" * 50
    print("\\n" + sep)
    print("  SYNC COMPLETE")
    print(f"  {{len(matched)}} cards UNSUSPENDED (ready to study)")
    print(f"  {{suspended}} cards remain suspended")
    print(sep)


if __name__ == "__main__":
    main()
'''


async def _get_filtered_note_ids(session_id: str, threshold: float) -> list[int]:
    """Fetch note IDs above the similarity threshold for a session."""
    pool = get_pool()
    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session_id format")

    async with pool.acquire() as conn:
        # Verify session exists
        exists = await conn.fetchval(
            "SELECT 1 FROM upload_sessions WHERE id=$1", sid
        )
        if not exists:
            raise HTTPException(404, "Session not found")

        rows = await conn.fetch(
            """
            SELECT note_id FROM match_results
            WHERE session_id = $1 AND similarity >= $2
            ORDER BY similarity DESC
            """,
            sid,
            threshold,
        )
    return [row["note_id"] for row in rows]


@router.get("/sync/script")
async def download_sync_script(
    session_id: str = Query(..., description="Session ID from upload"),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0, description="Similarity threshold"),
) -> Response:
    """Download a Python script to sync matched cards via AnkiConnect."""
    note_ids = await _get_filtered_note_ids(session_id, threshold)

    if not note_ids:
        raise HTTPException(404, f"No notes found above threshold {threshold}")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    script = SCRIPT_TEMPLATE.format(
        timestamp=timestamp,
        threshold=threshold,
        note_count=len(note_ids),
        deck_name=_DECK_NAME,
        note_ids=repr(note_ids),
    )

    return Response(
        content=script,
        media_type="text/x-python",
        headers={"Content-Disposition": "attachment; filename=sync_relevancy.py"},
    )


@router.get("/sync/search-query")
async def get_search_query(
    session_id: str = Query(..., description="Session ID from upload"),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0, description="Similarity threshold"),
) -> dict:
    """Return an Anki browser search query for the matched notes."""
    note_ids = await _get_filtered_note_ids(session_id, threshold)

    if not note_ids:
        return {"query": "", "note_count": 0}

    nid_part = ",".join(str(n) for n in note_ids)
    query = f'deck:"{_DECK_NAME}" nid:{nid_part}'

    return {"query": query, "note_count": len(note_ids)}


@router.get("/sync/note-ids")
async def download_note_ids(
    session_id: str = Query(..., description="Session ID from upload"),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0, description="Similarity threshold"),
) -> Response:
    """Download a plain-text file with one matched note ID per line."""
    note_ids = await _get_filtered_note_ids(session_id, threshold)
    content = "\n".join(str(nid) for nid in note_ids)

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=relevancy_note_ids.txt"
        },
    )
