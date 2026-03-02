"""Live API tests — require backend running at http://localhost:8000 with DB connected.

Run with: pytest tests/test_api.py -v --timeout=30
Skip if backend is not running (detected via health check).
"""

import io
import pytest

try:
    import httpx
    _httpx_available = True
except ImportError:
    _httpx_available = False

BASE = "http://localhost:8000"


def _backend_running() -> bool:
    """Return True if backend is running and healthy."""
    if not _httpx_available:
        return False
    try:
        r = httpx.get(f"{BASE}/health", timeout=3)
        return r.status_code == 200 and r.json().get("model_loaded", False)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _backend_running(),
    reason="Backend not running at localhost:8000 (start with: cd backend && uvicorn app.main:app)",
)


@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=BASE, timeout=60)


@pytest.fixture(scope="module")
def uploaded_session_id(client):
    """Upload a small test PDF and return the session ID."""
    # Create a minimal PDF-like text file for testing
    content = b"Heart sounds: S1 is closure of mitral and tricuspid valves."
    r = client.post(
        "/api/upload",
        files={"files": ("test.txt", content, "text/plain")},
    )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    return r.json()["session_id"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["model_loaded"] is True


def test_health_db_connected(client):
    r = client.get("/health")
    data = r.json()
    assert data["db_connected"] is True, "DB not connected — check DATABASE_URL"


def test_upload_invalid_type(client):
    r = client.post(
        "/api/upload",
        files={"files": ("test.exe", b"fake binary", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_upload_valid_txt(client):
    content = b"The mitral valve is a bicuspid valve between the left atrium and ventricle."
    r = client.post(
        "/api/upload",
        files={"files": ("test.txt", content, "text/plain")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["total_chunks"] >= 1
    assert data["status"] == "done"


def test_get_matches(client, uploaded_session_id):
    r = client.get(f"/api/match/{uploaded_session_id}")
    assert r.status_code == 200
    data = r.json()
    assert "cards" in data
    for card in data["cards"]:
        assert 0.0 <= card["similarity"] <= 1.0
        assert "note_id" in card
        assert "text" in card
        assert "tags" in card


def test_get_matches_invalid_session(client):
    r = client.get("/api/match/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_sync_script(client, uploaded_session_id):
    r = client.get(
        "/api/sync/script",
        params={"session_id": uploaded_session_id, "threshold": 0.0},
    )
    # If no matches, this may 404 — that's acceptable
    if r.status_code == 200:
        assert "text/x-python" in r.headers["content-type"]
        assert "NOTE_IDS" in r.text
        assert "AnkiConnect" in r.text or "ankiconnect" in r.text.lower()
    else:
        assert r.status_code == 404  # No cards above threshold


def test_sync_search_query(client, uploaded_session_id):
    r = client.get(
        "/api/sync/search-query",
        params={"session_id": uploaded_session_id, "threshold": 0.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert "query" in data
    if data["query"]:
        assert 'deck:"AnKing Step Deck"' in data["query"]
        assert "nid:" in data["query"]


def test_sync_note_ids(client, uploaded_session_id):
    r = client.get(
        "/api/sync/note-ids",
        params={"session_id": uploaded_session_id, "threshold": 0.0},
    )
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]


def test_relevancy_quality(client):
    """Upload cardiology text and verify meaningful matches are returned."""
    cardio_text = (
        "Heart sounds: S1 is closure of mitral and tricuspid valves. "
        "S2 is closure of aortic and pulmonic valves. "
        "Aortic stenosis causes a crescendo-decrescendo systolic murmur. "
        "The mitral valve has two cusps and separates the left atrium from left ventricle."
    ).encode()

    r = client.post(
        "/api/upload",
        files={"files": ("cardio.txt", cardio_text, "text/plain")},
        timeout=60,
    )
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    r = client.get(f"/api/match/{session_id}")
    assert r.status_code == 200
    data = r.json()

    # With a populated DB, we should get matches above 0.2 for cardiology text
    above_threshold = [c for c in data["cards"] if c["similarity"] > 0.2]
    assert len(above_threshold) >= 5, (
        f"Expected ≥5 cards above 0.2 similarity, got {len(above_threshold)}. "
        "Is anki_notes table populated? Run scripts/precompute_embeddings.py then upload."
    )

    # Top match should be fairly relevant
    if data["cards"]:
        top_sim = data["cards"][0]["similarity"]
        assert top_sim > 0.4, f"Top similarity {top_sim:.3f} too low for cardiology text"
