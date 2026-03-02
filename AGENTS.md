# Relevancey — Agent Definitions

## Agent Roles

### Architect
Coordinates implementation. Reads `todo/` prompts in order, delegates to sub-agents, updates `CLAUDE.md` checklist when prompts are completed.

**Tools**: All. **Context**: Full project.

### Anki-Parser
Implements and tests `packages/anki_parser/`. Focused entirely on `.apkg` parsing, HTML stripping, data models.

**Tools**: Read, Write, Edit, Bash (tests only). **Context**: `packages/anki_parser/`, `anking/`.

**Handoff**: Outputs a working `parse_apkg()` function verified against the AnKing deck (28,660 notes, 35,079 cards).

### Backend
Implements `backend/`. FastAPI routes, asyncpg DB pool, sentence-transformers embedding, document parsing, matching logic, sync API.

**Tools**: Read, Write, Edit, Bash. **Context**: `backend/`, `sql/`, `packages/anki_parser/`.

**Handoff**: All API endpoints passing tests. `uvicorn app.main:app` starts clean.

### Frontend
Implements `frontend/`. React + TypeScript + Vite + shadcn/ui. File upload, results list, relevancy slider, sync UI.

**Tools**: Read, Write, Edit, Bash. **Context**: `frontend/`.

**Handoff**: `npm run dev` loads the full UI. Upload → results → slider → sync flow works end-to-end against the backend.

### DevOps
Handles deployment (prompts 13-14). Supabase schema, Oracle Cloud setup, nginx config, Cloudflare Pages.

**Tools**: Read, Bash, WebFetch. **Context**: `sql/`, `scripts/`, `todo/13-deploy-supabase.md`, `todo/14-deploy-oracle-cloud.md`.

## Sub-Agent Usage Guidelines
- Launch **Anki-Parser** and **Frontend** agents in parallel (no dependency between them after prompt 01)
- Launch **Backend** only after **Anki-Parser** is done (backend imports `anki_parser`)
- Each agent should read its relevant `todo/` prompt before starting
- Agents write mistakes they discover to `CLAUDE.md` under `<!-- MISTAKES -->`
- Keep agent context focused — don't load the full 5.6GB Anki deck into context, only reference it via script output

### Tester-Local
Runs the full local test suite. Does not write production code — only writes tests and fixes them.

**Trigger**: After prompts 01–12 are complete. Both servers must be running (`localhost:8000` + `localhost:5173`).
**Tools**: Read, Bash, Write (test files only).
**Context**: Full project.
**Handoff**: Written report at `tests/local-test-report.md`. All 6 suites must pass before moving to prompt 13.
**Suites**: Anki parser pytest, backend unit pytest, live API (httpx), relevancy quality check, sync script dry-run, frontend smoke.

### Tester-Deployed
Validates the live production deployment. Never touches localhost.

**Trigger**: After prompt 14 (deployment) is complete.
**Tools**: Read, Bash.
**Context**: Needs `PRODUCTION_URL` and `FRONTEND_URL` env vars.
**Handoff**: Written report at `tests/deployed-test-report.md`. Must pass before the project is declared production-ready.
**Suites**: Availability & SSL, CORS, upload & match, performance benchmarks, sync endpoints, Supabase health, concurrency smoke test.

## Explore Agent Usage
Use the `Explore` subagent for:
- Finding where a class/function is defined across the codebase
- Searching for patterns in multiple files
- Answering "how does X work" questions without modifying files
