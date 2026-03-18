# Manual Start

## Prerequisites

Copy and configure the backend environment file if you haven't already:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your DATABASE_URL
```

## Backend

FastAPI on port 8020:

```bash
uv run --package relevancy-backend python -m uvicorn app.main:app --reload --port 8020 --app-dir backend
```

## Frontend

Vite on port 5173:

```bash
cd frontend
npm install   # first time only
npm run dev
```

## URLs

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:5173        |
| Backend  | http://localhost:8020        |
| Health   | http://localhost:8020/health |
| API docs | http://localhost:8020/docs   |

> The backend loads the `FremyCompany/BioLORD-2023` embedding model on startup — wait for the health endpoint to respond before using the app.
