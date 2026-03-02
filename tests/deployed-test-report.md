# Deployed Test Report
Date: (pending — run after prompt 14 deployment is complete)
Backend: https://your-domain.com
Frontend: https://YOUR_FRONTEND_DOMAIN

## Status: PENDING — deployment not yet complete

## How to Run
Set environment variables and run each suite manually:
```bash
export PRODUCTION_URL="https://your-domain.com"
export FRONTEND_URL="https://YOUR_FRONTEND_DOMAIN"

# Suite 1 — Availability & SSL
curl -sf "$PRODUCTION_URL/health" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'ok'
assert d['model_loaded'] is True
assert d['db_connected'] is True
print('Health: PASS')
"

# Suite 2 — CORS
curl -sf -X OPTIONS "$PRODUCTION_URL/api/upload" \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep -i "access-control-allow-origin"

# Suite 3 — Upload & Match
SESSION=$(curl -sf -X POST "$PRODUCTION_URL/api/upload" \
  -F "files=@/tmp/test_medical.txt" --max-time 60 \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
curl -sf "$PRODUCTION_URL/api/match/$SESSION" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Matched cards: {len(d[\"cards\"])}')
"

# Suite 6 — Supabase Health
curl -sf "$PRODUCTION_URL/api/stats" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Notes in DB: {d[\"anki_note_count\"]}')
print(f'DB size: {d[\"db_size_mb\"]}MB')
assert d['anki_note_count'] >= 28000, 'Too few notes'
print('Supabase health: PASS')
"
```

## Results
| Suite | Checks | Passed | Failed |
|-------|--------|--------|--------|
| 1 — Availability & SSL | — | — | — |
| 2 — CORS | — | — | — |
| 3 — Upload & Match | — | — | — |
| 4 — Performance | — | — | — |
| 5 — Sync Endpoints | — | — | — |
| 6 — Supabase Health | — | — | — |
| 7 — Concurrency | — | — | — |

## Performance Summary
| Operation | Time | Target | Status |
|-----------|------|--------|--------|
| Upload + match | — | <5000ms | — |
| Match retrieval | — | <500ms | — |

## Failures
(none recorded yet)

## Observations
(fill in after running)
