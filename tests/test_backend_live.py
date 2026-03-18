"""Live backend tests using real test documents.

Run with:
    uv run --package relevancy-backend python tests/test_backend_live.py

Requires:
    - Backend running at http://localhost:8000
    - test-documents/ directory with PDF and DOCX files
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import json

BACKEND = "http://localhost:8000"
TEST_DOCS = Path(__file__).resolve().parent.parent / "test-documents"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}{f' — {detail}' if detail else ''}")


def get(path: str) -> dict:
    r = urlopen(f"{BACKEND}{path}", timeout=30)
    return json.loads(r.read())


def upload_file(filepath: Path) -> dict:
    """Upload a file using multipart/form-data (stdlib only)."""
    boundary = "----TestBoundary123456"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="files"; filename="{filepath.name}"\r\n'.encode()
    )
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(filepath.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    req = Request(
        f"{BACKEND}/api/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    r = urlopen(req, timeout=120)
    return json.loads(r.read())


# ── Preflight ────────────────────────────────────────────────────────────────

print("\n=== Backend Live Tests ===\n")

print("[preflight]")
try:
    health = get("/health")
except (URLError, OSError) as e:
    print(f"  FAIL  Backend not reachable at {BACKEND}: {e}")
    sys.exit(1)

check("backend reachable", True)
check("model loaded", health["model_loaded"])
check("db connected", health["db_connected"], "check DATABASE_URL in backend/.env")

if not health["db_connected"]:
    print("\nStopping — database not connected.")
    sys.exit(1)

# ── Stats ────────────────────────────────────────────────────────────────────

print("\n[stats]")
stats = get("/api/stats")
check("anki notes loaded", stats["anki_note_count"] >= 28000, f"got {stats['anki_note_count']}")
print(f"         notes: {stats['anki_note_count']:,}  db: {stats['db_size_mb']} MB")

# ── Test document uploads ────────────────────────────────────────────────────

test_files = sorted(TEST_DOCS.glob("*"))
if not test_files:
    print(f"\n  SKIP  No test documents found in {TEST_DOCS}")
    sys.exit(0)

for filepath in test_files:
    suffix = filepath.suffix.lower()
    if suffix not in (".pdf", ".docx", ".pptx", ".txt", ".md"):
        continue

    print(f"\n[upload: {filepath.name}]")
    t0 = time.time()
    result = upload_file(filepath)
    elapsed = time.time() - t0

    check("status done", result["status"] == "done", f"got {result['status']}")
    check("chunks extracted", result["total_chunks"] > 0, f"got {result['total_chunks']}")
    check("matches found", result["match_count"] > 0, f"got {result['match_count']}")
    print(f"         chunks: {result['total_chunks']}  matches: {result['match_count']}  time: {elapsed:.1f}s")

    # Verify match retrieval
    session_id = result["session_id"]
    matches = get(f"/api/match/{session_id}")
    check("match retrieval works", len(matches["cards"]) == result["match_count"])

    # Verify matches are sorted by similarity descending
    sims = [c["similarity"] for c in matches["cards"]]
    check("sorted by similarity", sims == sorted(sims, reverse=True))

    # Verify top match is reasonably relevant
    if sims:
        check("top similarity > 0.3", sims[0] > 0.3, f"top sim: {sims[0]:.4f}")

    # Verify chunks were cleaned up
    # (We can't query DB directly, but we can check the match still works)
    check("session retrievable after cleanup", matches["status"] == "done")

# ── Rate limiting ────────────────────────────────────────────────────────────

print("\n[rate limiting]")
# Upload a small text file 11 times quickly to trigger the 10/min limit
hit_limit = False
for i in range(12):
    try:
        boundary = "----TestBoundary123456"
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(b'Content-Disposition: form-data; name="files"; filename="test.txt"\r\n')
        body.extend(b"Content-Type: text/plain\r\n\r\n")
        body.extend(b"Test content for rate limiting check.")
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = Request(
            f"{BACKEND}/api/upload",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        urlopen(req, timeout=120)
    except Exception as e:
        if "429" in str(e):
            hit_limit = True
            break
check("rate limit triggers", hit_limit, "sent 12 requests but never got 429")

# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("STATUS: FAIL")
    sys.exit(1)
else:
    print("STATUS: ALL PASS")
