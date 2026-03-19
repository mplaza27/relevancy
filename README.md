# Relevancey

Match uploaded medical lecture materials against AnKing Anki cards by semantic similarity.

**Live at [YOUR_FRONTEND_DOMAIN](https://YOUR_FRONTEND_DOMAIN)**

## What it does

Upload a PDF, PPTX, DOCX, TXT, or MD file from a lecture or textbook chapter. Relevancey finds the AnKing Step Deck cards most relevant to that material, lets you tune a relevancy threshold slider, and generates an Anki sync script to suspend/unsuspend cards in your local Anki.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + shadcn/ui + Tailwind |
| Backend | FastAPI + asyncpg (Python 3.12) |
| Embeddings | BioLORD-2023 (768-dim) + MedCPT-Cross-Encoder |
| Search | pgvector semantic + BM25 tsvector with RRF fusion → cross-encoder reranking |
| Database | Supabase free tier PostgreSQL + pgvector |
| Backend hosting | Oracle Cloud Always Free (4 ARM cores, 24GB RAM) |
| Frontend hosting | Cloudflare Pages |
| CI/CD | GitHub Actions (auto-deploy to Oracle on push) |

## How it works

1. **Upload** — backend extracts text and keywords, returns a session ID immediately
2. **Processing** — background task embeds chunks, runs hybrid search against 28,660 AnKing notes, reranks with cross-encoder
3. **Results** — frontend polls until done, then shows ranked cards with similarity scores
4. **Sync** — download a Python script that uses AnkiConnect to unsuspend only the matched cards in your local Anki

## Local development

**Backend:**
```bash
cd backend
cp .env.example .env  # fill in DATABASE_URL
python3.12 -m venv .venv
.venv/bin/pip install -e ../packages/anki_parser -e .
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --app-dir .
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev  # runs on http://localhost:5173
```

## Deployment

- **Backend**: Oracle Cloud Always Free at `https://YOUR_BACKEND_DOMAIN`, served via nginx + Let's Encrypt SSL
- **Frontend**: Cloudflare Pages at `https://YOUR_FRONTEND_DOMAIN`
- **Auto-deploy**: GitHub Actions SSHes into Oracle and restarts the service on every push to master

See `oracle-manual-steps.md` for the full Oracle setup guide.

## Database schema

See `sql/schema.sql`. Run migrations in order after initial setup:
- `sql/migration_v2_biolord.sql` — BioLORD-2023 (768-dim) + BM25 hybrid search
- `sql/migration_v3_async.sql` — keywords column for async upload pipeline

## Project structure

```
relevancy/
├── packages/anki_parser/   # Standalone Anki .apkg parser (reusable)
├── backend/app/            # FastAPI application
├── frontend/src/           # React application
├── scripts/                # Pre-compute embeddings + upload to Supabase
├── sql/                    # Schema + migrations
└── .github/workflows/      # CI/CD
```
