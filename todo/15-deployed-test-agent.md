[x]
# Prompt 15: Deployed Test Agent

## When to Run
After prompt 14 is complete and the production deployment is live.

## Goal
Define and run a specialized test agent that validates the production deployment end-to-end — from the live URL through to Supabase and back. Catches environment-specific failures that don't surface locally (CORS, SSL, cold-start latency, ARM CPU performance, Supabase connection limits).

## Agent Definition

Add this to `AGENTS.md`:

```
### Tester-Deployed
Validates the live production deployment. Runs against real URLs only — never localhost. Does not modify production code. Reports failures as GitHub issues or to a local report file.

**Trigger**: After prompt 14 (deployment) is complete.
**Tools**: Read, Bash, WebFetch.
**Context**: Needs PRODUCTION_URL and FRONTEND_URL from environment.
**Handoff**: Written report at `tests/deployed-test-report.md`. Must pass before the project is considered production-ready.
```

## Pre-conditions

The agent reads these from environment or prompts the user:
```bash
PRODUCTION_URL="https://your-domain.com"        # Oracle Cloud backend
FRONTEND_URL="https://relevancey.pages.dev"     # Cloudflare Pages frontend
```

## Test Suites

### Suite 1 — Availability & SSL
```bash
# Backend is reachable and HTTPS is valid
curl -sf --max-time 10 "$PRODUCTION_URL/health" || echo "FAIL: backend unreachable"

# SSL certificate is valid (not self-signed, not expired)
curl -sf --max-time 10 "$PRODUCTION_URL/health" 2>&1 | grep -v "SSL" || echo "FAIL: SSL error"

# Frontend is reachable
curl -sf --max-time 10 "$FRONTEND_URL" | grep -q "Relevancey" || echo "FAIL: frontend unreachable"

# Backend health returns expected fields
curl -sf "$PRODUCTION_URL/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok', f'status={d[\"status\"]}'
assert d['model_loaded'] is True, 'model not loaded'
assert d['db_connected'] is True, 'db not connected'
print('Health: PASS')
"
```

### Suite 2 — CORS Validation
Confirm the frontend origin is allowed by the backend:
```bash
# Simulate a preflight from the frontend origin
curl -sf -X OPTIONS "$PRODUCTION_URL/api/upload" \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -i "access-control-allow-origin" || echo "FAIL: CORS not configured"

# Verify the exact origin is allowed (not just *)
curl -sf "$PRODUCTION_URL/health" \
  -H "Origin: $FRONTEND_URL" \
  -I 2>&1 | grep -i "access-control"
```

### Suite 3 — Upload & Match (Production)
```bash
# Create a small test PDF with medical text
python3 - << 'EOF'
from reportlab.pdfgen import canvas
import tempfile, os

text = """
Heart sounds: S1 closure of mitral and tricuspid valves.
S2 closure of aortic and pulmonic valves.
Aortic stenosis: crescendo-decrescendo systolic murmur at RUSB.
Mitral regurgitation: holosystolic murmur at apex radiating to axilla.
"""

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
    c = canvas.Canvas(f.name)
    y = 750
    for line in text.strip().split('\n'):
        c.drawString(50, y, line)
        y -= 20
    c.save()
    print(f.name)
EOF
```

If `reportlab` isn't available, use any small medical-content PDF.

```bash
# Upload to production
SESSION=$(curl -sf -X POST "$PRODUCTION_URL/api/upload" \
  -F "files=@/tmp/test_medical.pdf" \
  --max-time 60 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "Session ID: $SESSION"

# Get match results
RESULTS=$(curl -sf "$PRODUCTION_URL/api/match/$SESSION" --max-time 30)
CARD_COUNT=$(echo $RESULTS | python3 -c "import sys,json; print(len(json.load(sys.stdin)['cards']))")

echo "Matched cards: $CARD_COUNT"
[ "$CARD_COUNT" -gt "0" ] || echo "FAIL: no cards matched"
```

### Suite 4 — Performance Benchmarks
Validate response times meet requirements from the PRD (< 5 seconds for a typical PDF):

```bash
# Time the full upload-to-results flow
START=$(date +%s%N)
SESSION=$(curl -sf -X POST "$PRODUCTION_URL/api/upload" \
  -F "files=@/tmp/test_medical.pdf" --max-time 60 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))

echo "Upload + match time: ${ELAPSED_MS}ms"
[ "$ELAPSED_MS" -lt "10000" ] || echo "WARN: upload took more than 10s (${ELAPSED_MS}ms)"
[ "$ELAPSED_MS" -lt "5000" ] && echo "PASS: under 5s target" || echo "WARN: over 5s target"

# Time match result retrieval (should be fast — just a DB read)
START=$(date +%s%N)
curl -sf "$PRODUCTION_URL/api/match/$SESSION" > /dev/null
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))
echo "Match retrieval time: ${ELAPSED_MS}ms"
[ "$ELAPSED_MS" -lt "500" ] || echo "WARN: match retrieval slow (${ELAPSED_MS}ms)"
```

### Suite 5 — Sync Endpoints
```bash
# Script download
curl -sf "$PRODUCTION_URL/api/sync/script?session_id=$SESSION&threshold=0.3" \
  -o /tmp/test_sync_script.py
grep -q "NOTE_IDS" /tmp/test_sync_script.py || echo "FAIL: NOTE_IDS not in script"
grep -q "ankiconnect" /tmp/test_sync_script.py || echo "FAIL: ankiconnect not in script"
python3 -c "import ast; ast.parse(open('/tmp/test_sync_script.py').read()); print('Script syntax: PASS')"

# Search query
QUERY=$(curl -sf "$PRODUCTION_URL/api/sync/search-query?session_id=$SESSION&threshold=0.3" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['query'])")
echo "$QUERY" | grep -q 'deck:"AnKing Step Deck"' || echo "FAIL: deck name missing from query"
echo "$QUERY" | grep -q 'nid:' || echo "FAIL: nid: missing from query"

# Note ID list
curl -sf "$PRODUCTION_URL/api/sync/note-ids?session_id=$SESSION&threshold=0.3" \
  | head -3
```

### Suite 6 — Supabase Health
```bash
# Verify note count in production DB (via backend)
NOTE_COUNT=$(curl -sf "$PRODUCTION_URL/api/stats" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['anki_note_count'])" 2>/dev/null)

echo "Anki notes in DB: $NOTE_COUNT"
[ "$NOTE_COUNT" -ge "28000" ] || echo "FAIL: note count low ($NOTE_COUNT), embeddings may not be fully uploaded"

# Verify DB size is under free tier limit
DB_SIZE=$(curl -sf "$PRODUCTION_URL/api/stats" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('db_size_mb', 'unknown'))" 2>/dev/null)
echo "DB size: ${DB_SIZE}MB (limit: 500MB)"
```

Note: This requires adding a `GET /api/stats` endpoint to the backend (the agent adds this if missing):
```python
@app.get("/api/stats")
async def get_stats(pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        note_count = await conn.fetchval("SELECT COUNT(*) FROM anki_notes")
        db_size = await conn.fetchval(
            "SELECT pg_database_size(current_database()) / 1024 / 1024"
        )
    return {"anki_note_count": note_count, "db_size_mb": db_size}
```

### Suite 7 — Concurrency Smoke Test
Simulate a few concurrent users uploading at the same time:
```bash
# Fire 3 uploads in parallel
for i in 1 2 3; do
  curl -sf -X POST "$PRODUCTION_URL/api/upload" \
    -F "files=@/tmp/test_medical.pdf" --max-time 60 &
done
wait
echo "Concurrent uploads: complete"
```

Verify the server didn't crash:
```bash
curl -sf "$PRODUCTION_URL/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok'
print('Server still healthy after concurrent load: PASS')
"
```

## Test Report

The agent writes `tests/deployed-test-report.md`:

```markdown
# Deployed Test Report
Date: {timestamp}
Backend: {PRODUCTION_URL}
Frontend: {FRONTEND_URL}

## Results
| Suite | Checks | Passed | Failed |
|-------|--------|--------|--------|
| Availability & SSL | N | N | N |
| CORS | N | N | N |
| Upload & Match | N | N | N |
| Performance | N | N | N |
| Sync Endpoints | N | N | N |
| Supabase Health | N | N | N |
| Concurrency | N | N | N |

## Performance Summary
| Operation | Time | Target | Status |
|-----------|------|--------|--------|
| Upload + match | Xms | <5000ms | PASS/FAIL |
| Match retrieval | Xms | <500ms | PASS/FAIL |

## Status: PASS / FAIL

## Failures
(specific failures with curl output)

## Observations
(anything notable: cold start times, memory warnings, Supabase connection pooling, etc.)
```

## Pass Criteria
- All 7 suites pass
- Upload + match time < 10 seconds (warn if > 5s)
- Match retrieval < 500ms
- At least 28,000 notes in production DB
- Server remains healthy after concurrency test

Any failure blocks the project from being declared production-ready. The report is kept at `tests/deployed-test-report.md` as a permanent record.
