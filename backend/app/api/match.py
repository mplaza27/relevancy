from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.database import get_pool

router = APIRouter()


@router.get("/match/{session_id}")
async def get_matches(session_id: str) -> dict:
    """Retrieve cached match results for a session.

    Returns all matched Anki notes sorted by similarity descending.
    The frontend applies the relevancy threshold slider client-side.
    """
    pool = get_pool()

    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session_id format")

    async with pool.acquire() as conn:
        # Verify session exists
        session = await conn.fetchrow(
            "SELECT id, status FROM upload_sessions WHERE id=$1",
            sid,
        )
        if not session:
            raise HTTPException(404, "Session not found")

        rows = await conn.fetch(
            """
            SELECT m.note_id, m.similarity,
                   n.notetype, n.text, n.extra, n.tags, n.raw_fields
            FROM match_results m
            JOIN anki_notes n ON m.note_id = n.note_id
            WHERE m.session_id = $1
            ORDER BY m.similarity DESC
            """,
            sid,
        )

    return {
        "session_id": session_id,
        "status": session["status"],
        "cards": [
            {
                "note_id": row["note_id"],
                "text": row["text"],
                "extra": row["extra"] or "",
                "tags": list(row["tags"] or []),
                "notetype": row["notetype"],
                "similarity": round(float(row["similarity"]), 4),
                "raw_fields": json.loads(row["raw_fields"]) if isinstance(row["raw_fields"], str) else (row["raw_fields"] or {}),
            }
            for row in rows
        ],
    }
