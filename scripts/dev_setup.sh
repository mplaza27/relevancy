#!/bin/bash
# Set up the full development environment for Relevancey
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "=== Relevancey Dev Setup ==="

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Install anki_parser
echo "Installing anki_parser..."
uv pip install -e packages/anki_parser

# Install backend deps
echo "Installing backend deps..."
uv pip install fastapi "uvicorn[standard]" asyncpg "pgvector>=0.3" \
    sentence-transformers pymupdf4llm python-pptx python-docx \
    python-multipart numpy pydantic-settings pytest pytest-asyncio httpx
uv pip install -e backend/ --no-deps

# Install frontend
echo "Installing frontend..."
cd frontend && npm install && cd ..

echo ""
echo "=== Setup complete ==="
echo ""
echo "Run the backend:"
echo "  cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo ""
echo "Run the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "Run tests:"
echo "  Backend: cd backend && PYTHONPATH=. ../.venv/bin/python -m pytest tests/"
echo "  Anki parser: .venv/bin/python -m pytest packages/anki_parser/tests/"
