[x]
# Prompt 01: Project Scaffolding

## Goal
Set up the monorepo directory structure, dependencies, and configuration files for the Relevancey project.

## Context
- Working directory: `/home/vega/code-projects/relevancey/`
- Python 3.12+ (check `.python-version`)
- The `anking/` directory already exists with `AnKing Step Deck.apkg` (5.6GB) and a `__MACOSX` folder (delete this)
- Existing files: `main.py` (placeholder), `pyproject.toml` (empty deps), `README.md`, `.gitignore`

## Tasks

### 1. Clean up existing files
- Delete `__MACOSX` folder from `anking/`
- Delete placeholder `main.py`

### 2. Create the directory structure
```
relevancey/
├── packages/
│   └── anki_parser/           # Standalone package (own pyproject.toml)
│       ├── src/
│       │   └── anki_parser/
│       │       ├── __init__.py
│       │       ├── apkg.py
│       │       ├── database.py
│       │       ├── models.py
│       │       ├── text.py
│       │       ├── media.py
│       │       └── py.typed
│       ├── tests/
│       │   └── __init__.py
│       └── pyproject.toml
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Settings / env vars
│   │   ├── database.py        # asyncpg pool + pgvector
│   │   ├── embeddings.py      # sentence-transformers model
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py
│   │   │   ├── match.py
│   │   │   └── sync.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── document_parser.py
│   │       ├── chunker.py
│   │       ├── matcher.py
│   │       └── deck_service.py
│   ├── tests/
│   │   └── __init__.py
│   └── pyproject.toml
│
├── frontend/                  # Created by Vite in prompt 09
│
├── scripts/
│   └── precompute_embeddings.py
│
├── sql/
│   └── schema.sql             # Supabase schema
│
├── anking/                    # Raw deck (gitignored)
├── todo/                      # These prompt files
├── PRD.md
├── pyproject.toml             # Root project (workspace)
├── .gitignore
└── README.md
```

### 3. Root `pyproject.toml`
Update the existing root `pyproject.toml` to be a workspace coordinator:
```toml
[project]
name = "relevancey"
version = "0.1.0"
description = "Match lecture materials to Anki flashcards by semantic relevancy"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM"]
```

### 4. `packages/anki_parser/pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "anki-parser"
version = "0.1.0"
description = "Standalone read-only parser for Anki .apkg files"
requires-python = ">=3.12"
license = "MIT"
dependencies = [
    "zstandard>=0.22.0",
    "selectolax>=0.3.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/anki_parser"]
```

### 5. `backend/pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "relevancey-backend"
version = "0.1.0"
description = "Relevancey FastAPI backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "asyncpg>=0.30",
    "pgvector>=0.3",
    "sentence-transformers>=3.0",
    "pymupdf4llm>=0.0.17",
    "python-pptx>=1.0",
    "python-docx>=1.1",
    "python-multipart>=0.0.9",
    "numpy>=1.26",
    "anki-parser @ file:///${PROJECT_ROOT}/../packages/anki_parser",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

### 6. Update `.gitignore`
Add to the existing `.gitignore`:
```
# Anki data (large files)
anking/
*.apkg
*.apkg.zip

# macOS
__MACOSX/

# Environment
.env
.env.local

# Node
node_modules/
dist/

# Python
__pycache__/
*.py[oc]
build/
*.egg-info
.venv

# IDE
.vscode/
.idea/

# Temp files
*.tmp
```

### 7. Create all `__init__.py` files
Empty `__init__.py` in every Python package directory.

## Verification
- All directories exist
- Both `pyproject.toml` files are valid
- `anki_parser` package can be installed in editable mode: `pip install -e packages/anki_parser`
- No `__MACOSX` folder remains
