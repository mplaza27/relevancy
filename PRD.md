# Relevancey - Product Requirements Document

## Overview

Relevancey is a web application for medical students that matches uploaded learning resources (PDFs, PPTs, DOCX, etc.) against an Anki flashcard deck to surface the most relevant cards for study. Users control a relevancy threshold via a slider, enabling personalized study sessions driven by their course materials.

## Problem Statement

Medical students use Anki decks containing tens of thousands of cards (e.g., AnKing Step Deck: ~28,660 notes / ~35,079 cards). When studying for a specific lecture, exam, or rotation, manually finding relevant cards is tedious. Relevancey automates this by semantically matching uploaded resources to cards.

## Target Users

- Medical students (MS1-MS4) using Anki for board prep (Step 1/2/3)
- Initial capacity: 5-200 concurrent users
- Primary Anki deck: AnKing Step Deck
- **No authentication** — anonymous, session-based usage

## Core Features (MVP)

### 1. Document Upload & Processing
- **Supported formats**: PDF, PPTX, DOCX, TXT, MD
- Users upload one or more files per session
- Backend extracts text content, including OCR for image-heavy PDFs
- Large files are chunked for processing

### 2. Anki Deck Ingestion
- Parse `.apkg` files (zip containing zstd-compressed SQLite + media)
- Extract note fields: `Text`, `Extra`, `Lecture Notes`, tags, and associated media references
- Support both note types in AnKing: `AnKingOverhaul` (text-based cloze cards) and `IO-one by one` (image occlusion)
- Strip HTML, extract plain text and cloze content for embedding
- Store parsed deck in vector database with metadata (tags, deck, note type, card IDs)

### 3. Semantic Relevancy Matching
- Generate embeddings for both uploaded content and Anki cards
- Use cosine similarity to rank cards against uploaded material
- Return ranked list of relevant cards with similarity scores

### 4. Relevancy Slider
- Frontend slider control (0.0 - 1.0) adjusting the similarity threshold
- Lower threshold = more cards returned (broader match)
- Higher threshold = fewer cards returned (stricter match)
- Real-time filtering without re-running the embedding pipeline

### 5. Results Display
- Show matched cards with:
  - Card text (rendered from HTML, cloze deletions shown)
  - Similarity score / relevancy percentage
  - Tags (hierarchical AnKing tags)
  - Source field (which part of the upload matched)
- Sortable by relevancy, tag, or deck section
- Expandable card detail view (Extra, Pathoma, B&B, Sketchy references)

### 6. Anki Card Control (Suspend/Unsuspend)
The goal is maximum automation for managing cards in the user's local Anki. **Both methods below are MVP features.**

#### Method A — AnkiConnect Helper Script (Primary)
- Users install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on (exposes REST API on `localhost:8765`)
- The website provides a **"Sync to Anki"** button that generates a downloadable Python script
- The script does the following when run locally with Anki open:
  1. Connects to AnkiConnect on `localhost:8765`
  2. Finds all card IDs in the target deck
  3. Suspends all cards in the deck
  4. Unsuspends only the matched/relevant card IDs
  5. Prints a summary (X cards unsuspended, Y cards suspended)
- User opens Anki and studies only the relevant, unsuspended cards

**Workflow:**
1. User uploads a lecture PDF → gets relevant cards with relevancy slider tuned
2. User clicks **"Download Anki Sync Script"** → gets a `.py` file with the matched card IDs baked in
3. User runs `python sync_relevancy.py` locally with Anki open
4. Done — Anki now has only the relevant cards unsuspended

#### Method B — Manual Fallbacks (Always Available)
These are always shown alongside Method A in the UI:

1. **Anki Search Query** — A copyable search string (e.g., `nid:1368291917470 OR nid:1368292036212 OR ...`) that users paste directly into Anki's Browse window to select matched cards. Includes a "Copy to Clipboard" button.

2. **Card ID List** — A downloadable `.txt` file with one note ID per line, for users who want to script their own workflow or use other tools.

3. **Filtered Deck Export** — Export a `.apkg` file containing only the matched cards, which users can import as a separate study deck in Anki.

## Stretch Goals (Post-MVP)

### AI-Generated Questions
- Given the matched content, generate practice questions (MCQ, short answer)
- Based on the uploaded material + matched Anki card context

### Helpful Links
- Auto-link matched cards to external resources (First Aid pages, Pathoma chapters, Sketchy videos)
- Leverage existing AnKing tag hierarchy for resource mapping

### Additional Deck Support
- Allow users to upload their own Anki decks
- Support for non-medical decks

## Architecture

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React + TypeScript (Vite) | Fast, modern, good component ecosystem |
| **Backend API** | FastAPI (Python) | Async, great for ML workloads, matches Anki tooling |
| **Vector DB** | pgvector (PostgreSQL via Supabase) | Free tier, pgvector included, 500MB |
| **Embeddings** | `all-MiniLM-L6-v2` (Sentence Transformers) | Free, fast on CPU, 384-dim vectors (small storage footprint) |
| **File Processing** | `pymupdf`, `python-pptx`, `python-docx` | Proven Python extraction libraries |
| **Hosting (Backend)** | Oracle Cloud Always Free | 4 ARM cores, 24GB RAM, always free |
| **Hosting (Frontend)** | Cloudflare Pages | Unlimited bandwidth, free |
| **CI/CD** | GitHub Actions | Standard, free for public repos |

### Embedding Strategy

**Pre-computation (one-time, on local 3080 FE):**
- Generate embeddings for all 28,660 Anki notes using `all-MiniLM-L6-v2` on GPU
- 384-dimensional vectors × 28,660 notes ≈ **44MB** storage in pgvector
- Upload pre-computed embeddings to Supabase
- This runs in seconds on a 3080 (10GB VRAM is massive overkill for an 80MB model)

**Runtime (on server, for user uploads):**
- `all-MiniLM-L6-v2` runs fast on **CPU only** — no GPU needed on server
- A typical lecture PDF (chunked into ~20 passages) embeds in < 2 seconds on CPU
- Zero API costs, no rate limits, no external dependencies
- Alternative fallback: Google Gemini embedding API (free tier) if CPU is too slow

**Why not a larger model?**
- `all-MiniLM-L6-v2` (22M params, 80MB) is the sweet spot for this use case
- Medical vocabulary is well-represented in its training data
- 384-dim vectors keep Supabase storage under the 500MB free limit
- Upgrading to `bge-large-en-v1.5` (1.3GB, 1024-dim) is easy later if quality needs improvement

### System Diagram

```
┌─────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Cloudflare     │       │  Oracle Cloud    │       │  Supabase        │
│  Pages          │──────▶│  Always Free     │──────▶│  Free Tier       │
│  (React UI)     │◀──────│  (FastAPI)       │◀──────│  (PostgreSQL +   │
└─────────────────┘       │                  │       │   pgvector)      │
                          │  - Upload parse  │       └──────────────────┘
                          │  - Embed (CPU)   │
                          │  - Match         │
                          └──────────────────┘
                                  │
                          ┌───────▼──────────┐
                          │  User's Local    │
                          │  Anki + Connect  │
                          │  (via helper     │
                          │   script)        │
                          └──────────────────┘
```

### Key Data Flow

1. **Deck Ingestion (one-time, local)**
   - Unzip `.apkg` → decompress zstd → read SQLite
   - Parse notes: strip HTML, extract text from each field
   - Generate embeddings on local 3080 FE (fast)
   - Upload embeddings + metadata to Supabase pgvector

2. **Document Upload (per request)**
   - User uploads file → backend extracts text
   - Chunk into passages (~512 tokens each)
   - Generate embeddings on server CPU (`all-MiniLM-L6-v2`)

3. **Matching**
   - Query pgvector: find top-K cards similar to each document chunk
   - Aggregate and deduplicate results across chunks
   - Apply relevancy threshold filter
   - Return ranked card list

4. **Anki Sync**
   - User clicks "Sync to Anki" → gets a helper script with matched card IDs
   - Script calls AnkiConnect API locally to suspend/unsuspend cards

## Module Structure (Transferability)

The Anki parsing logic must be a standalone, reusable package for the `pro-me` project.

```
relevancy/
├── packages/
│   └── anki_parser/              # STANDALONE — transferable to pro-me
│       ├── __init__.py
│       ├── apkg.py               # .apkg extraction (zip + zstd + sqlite)
│       ├── notes.py              # Note parsing, field extraction, HTML stripping
│       ├── models.py             # Data classes (Note, Card, Field, Deck, Tag)
│       ├── media.py              # Media file extraction and mapping
│       └── export.py             # Create .apkg files from card sets
│
├── backend/
│   ├── api/                      # FastAPI routes
│   │   ├── upload.py             # File upload endpoints
│   │   ├── match.py              # Relevancy matching endpoints
│   │   ├── decks.py              # Deck management endpoints
│   │   └── sync.py               # AnkiConnect script generation
│   ├── services/
│   │   ├── document_parser.py    # PDF/PPTX/DOCX text extraction
│   │   ├── embeddings.py         # Embedding generation (sentence-transformers)
│   │   ├── matcher.py            # Vector similarity search + ranking
│   │   └── deck_service.py       # Deck ingestion orchestration
│   ├── db/
│   │   ├── models.py             # SQLAlchemy models
│   │   └── migrations/           # Alembic migrations
│   └── main.py                   # FastAPI app entry point
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── RelevancySlider.tsx
│   │   │   ├── CardList.tsx
│   │   │   ├── CardDetail.tsx
│   │   │   └── SyncToAnki.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   └── Upload.tsx
│   │   └── App.tsx
│   └── package.json
│
├── scripts/
│   └── precompute_embeddings.py  # Run locally on 3080 to generate embeddings
│
├── anking/                       # Raw deck data (gitignored)
├── PRD.md
├── pyproject.toml
└── README.md
```

## Anki Data Reference

From the AnKing Step Deck analysis:

| Property | Value |
|----------|-------|
| Total notes | 28,660 |
| Total cards | 35,079 |
| Note types | `AnKingOverhaul` (text cloze), `IO-one by one` (image occlusion) |
| Media files | ~40,570 (images, audio) |
| Key fields (AnKingOverhaul) | Text, Extra, Lecture Notes, Missed Questions, Pathoma, B&B, First Aid, Sketchy, Picmonic, Pixorize, Physeo, Bootcamp, OME, Additional Resources |
| Key fields (IO) | Image, Header, Extra, Personal Notes, Missed Questions |
| Tag format | Hierarchical, `::` delimited (e.g., `#AK_Step1_v12::#FirstAid::07_Cardiovascular`) |
| File format | `.apkg` = zip containing zstd-compressed SQLite (`collection.anki21b`) + numbered media files |

## Deployment Plan — $0/month

### Option A: Oracle Cloud + Supabase (Recommended)

Best for long-term free hosting. Oracle's Always Free tier never expires and has far more resources.

| Service | What | Free Tier Details |
|---------|------|-------------------|
| **Oracle Cloud Always Free** | Backend (FastAPI) | 4 ARM Ampere cores, 24GB RAM, 200GB storage — **never expires** |
| **Supabase Free** | PostgreSQL + pgvector | 500MB database, 1GB file storage — pauses after 7 days inactivity |
| **Cloudflare Pages** | Frontend (React) | Unlimited bandwidth, 500 builds/month — always free |
| **Sentence Transformers** | Embeddings | Self-hosted on server CPU, zero cost |
| **GitHub Actions** | CI/CD | Free for public repos |
| **Total** | | **$0/month forever** |

**Why Oracle over AWS:** 24GB RAM easily fits FastAPI + the sentence-transformers model (~300MB loaded) with massive headroom for concurrent requests. AWS free tier only gives 1GB RAM which is dangerously tight.

### Option B: AWS Free Tier (12-Month Alternative)

Works if you prefer AWS, but **expires after 12 months** then costs ~$15-25/month.

| Service | What | Free Tier Details |
|---------|------|-------------------|
| **EC2** | Backend (FastAPI) | `t2.micro` — 1 vCPU, 1GB RAM, 750 hrs/month (12 months) |
| **RDS** | PostgreSQL + pgvector | `db.t2.micro` — 1 vCPU, 1GB RAM, 20GB storage (12 months) |
| **S3** | File storage | 5GB, 20K GET / 2K PUT per month (12 months) |
| **CloudFront** | Frontend CDN | 1TB transfer, 10M requests/month (12 months) |
| **Lambda** | Optional async tasks | 1M requests/month, 400K GB-seconds (**always free**) |
| **Total** | | **$0/month for 12 months, then ~$15-25/month** |

**AWS caveats:**
- 1GB RAM on `t2.micro` is tight — FastAPI (~100MB) + sentence-transformers model (~300MB) + request overhead leaves little room. May need to load/unload the model or use a smaller embedding approach.
- RDS `db.t2.micro` is fine for pgvector with our data volume.
- After 12 months, the cheapest path is ~$15/month (t3.nano + db.t4g.micro).

### Option C: Hybrid (Mix and Match)

| Service | Provider | Notes |
|---------|----------|-------|
| Backend | Oracle Cloud Always Free | Best free compute |
| Database | AWS RDS Free Tier | If you want pgvector on AWS for 12 months |
| Database (alt) | Supabase Free | If you want always-free |
| Frontend | Cloudflare Pages | Best free static hosting |

### Storage Budget (Supabase 500MB or RDS 20GB)

| Data | Estimated Size |
|------|---------------|
| 28,660 note embeddings (384-dim float32) | ~44MB |
| Note metadata (text, tags, IDs) | ~50MB |
| Indexes | ~30MB |
| Headroom for user session data | ~376MB (Supabase) or ~19.8GB (RDS) |
| **Total** | **~124MB used** |

### Supabase Inactivity Note
Supabase free tier pauses databases after 7 days of no activity. For a tool with 5-200 users, this shouldn't be an issue — but if it is, a simple cron ping from the backend server keeps it alive.

### Migration Path (if scaling beyond free)
- Oracle Cloud → any VPS ($5-10/mo on Hetzner, DigitalOcean)
- Supabase free → Supabase Pro ($25/mo) or self-hosted PostgreSQL
- AWS free → stay on AWS with reserved instances for lower cost
- Add a CDN for media files if needed

## Non-Functional Requirements

- **Response time**: Card matching results in < 5 seconds for a typical lecture PDF
- **Upload limit**: 50MB per file, 5 files per session
- **Concurrent users**: 5-200 supported
- **No auth required**: Anonymous, session-based
- **Data privacy**: Uploaded files are processed and deleted after session; no long-term storage
- **Availability**: Best-effort (free tier); aim for 95%+ uptime

## Success Metrics

- Users can upload a lecture PDF and receive relevant Anki cards within 5 seconds
- Relevancy slider meaningfully changes the result set
- Matched cards align with the topic of the uploaded material (validated by manual review)
- Anki suspend/unsuspend workflow completes in under 30 seconds
