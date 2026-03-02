# Relevancey - Implementation Prompts Overview

## Prompt Execution Order

Each prompt is a self-contained agent task. Execute them in order — later prompts depend on earlier ones.

| # | Prompt | Description | Depends On |
|---|--------|-------------|------------|
| 01 | Project Scaffolding | Set up monorepo structure, pyproject.toml, gitignore | — |
| 02 | Anki Parser Package | Standalone `anki_parser` package (transferable to pro-me) | 01 |
| 03 | Pre-compute Embeddings Script | Local script to embed all 28,660 notes on 3080 FE | 02 |
| 04 | Database Schema & Supabase | pgvector tables, HNSW indexes, Supabase setup SQL | 01 |
| 05 | Backend Core & Embedding Service | FastAPI app, embedding model loading, async patterns | 01, 04 |
| 06 | Document Parsing Service | PDF/PPTX/DOCX extraction + text chunking | 05 |
| 07 | Upload & Match API | File upload endpoint, vector search, relevancy matching | 05, 06 |
| 08 | Anki Sync API | Script generation endpoint + search query builder | 07 |
| 09 | Frontend Setup & File Upload | Vite + React + shadcn/ui, drag-drop upload component | 01 |
| 10 | Frontend Results & Slider | Card list, relevancy slider, expandable details | 09 |
| 11 | Frontend Anki Sync UI | Script download, copy search query, ID list export | 10 |
| 12 | Integration & Testing | End-to-end test, connect frontend to backend | 07, 11 |
| 12B | Local Test Agent | Specialized agent runs full local test suite — must pass before deployment | 12 |
| 13 | Deployment - Supabase | Set up Supabase project, run schema, upload embeddings | 03, 04 |
| 14 | Deployment - Oracle Cloud | Set up OCI Always Free VM, deploy backend + frontend | 12B, 13 |
| 15 | Deployed Test Agent | Specialized agent validates production deployment end-to-end | 14 |

## Architecture Decisions (Locked In)

- **Embeddings**: `all-MiniLM-L6-v2` (384-dim, 80MB model, runs on CPU)
- **Pre-compute**: Run on local 3080 FE, upload to Supabase
- **Runtime embedding**: CPU on Oracle Cloud ARM (24GB RAM)
- **Database**: Supabase free tier PostgreSQL + pgvector (HNSW index)
- **Frontend**: React + TypeScript + Vite + shadcn/ui + Tailwind
- **Backend**: FastAPI + asyncpg + sentence-transformers
- **Auth**: None (anonymous, session-based)
- **Anki sync**: AnkiConnect helper script + manual fallbacks (search query, ID list, filtered deck)
- **Hosting**: Oracle Cloud Always Free (backend) + Cloudflare Pages (frontend) + Supabase (DB) = $0/month
