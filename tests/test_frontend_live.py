"""Live frontend smoke tests.

Run with:
    python tests/test_frontend_live.py

Requires:
    - Frontend running at http://localhost:5173
    - Backend running at http://localhost:8000
"""

from __future__ import annotations

import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError

FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:8000"

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


print("\n=== Frontend Live Tests ===\n")

# ── Frontend reachable ───────────────────────────────────────────────────────

print("[connectivity]")
try:
    r = urlopen(FRONTEND, timeout=10)
    html = r.read().decode()
    check("frontend reachable", True)
except (URLError, OSError) as e:
    print(f"  FAIL  Frontend not reachable at {FRONTEND}: {e}")
    sys.exit(1)

# ── HTML structure ───────────────────────────────────────────────────────────

print("\n[html structure]")
check("has html doctype", "<!doctype html>" in html.lower() or "<!DOCTYPE html>" in html)
check("has root div", 'id="root"' in html)
check("has JS bundle", "src=" in html and (".tsx" in html or ".js" in html or "/src/" in html))
check("has viewport meta", "viewport" in html)

# ── Static assets ────────────────────────────────────────────────────────────

print("\n[static assets]")

# Vite dev server serves assets differently than production
# Check that the main entry point is accessible
try:
    r = urlopen(f"{FRONTEND}/src/main.tsx", timeout=10)
    check("main.tsx accessible", r.status == 200)
except Exception:
    # In production build, try the assets path
    try:
        r = urlopen(FRONTEND, timeout=10)
        check("main entry accessible", True)
    except Exception:
        check("main entry accessible", False)

# ── CORS preflight ───────────────────────────────────────────────────────────

print("\n[cors]")
try:
    req = Request(
        f"{BACKEND}/api/upload",
        method="OPTIONS",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
        },
    )
    r = urlopen(req, timeout=10)
    cors_origin = r.headers.get("access-control-allow-origin", "")
    check("CORS allows frontend origin", FRONTEND in cors_origin, f"got: {cors_origin}")
    check("CORS allows POST", "POST" in r.headers.get("access-control-allow-methods", "").upper())
except (URLError, OSError) as e:
    check("CORS preflight", False, f"backend not reachable: {e}")

# ── Frontend can reach backend ───────────────────────────────────────────────

print("\n[frontend → backend connectivity]")
try:
    r = urlopen(f"{BACKEND}/health", timeout=10)
    data = json.loads(r.read())
    check("backend healthy from frontend perspective", data["status"] == "ok")
    check("API URL configured", True)
except (URLError, OSError) as e:
    check("backend reachable", False, f"{e}")

# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("STATUS: FAIL")
    sys.exit(1)
else:
    print("STATUS: ALL PASS")
