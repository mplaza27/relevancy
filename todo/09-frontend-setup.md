[x]
# Prompt 09: Frontend Setup & File Upload

## Goal
Create the React + TypeScript frontend with Vite, set up shadcn/ui + Tailwind, and implement the file upload component with drag-and-drop.

## Context
- Location: `frontend/` in the project root
- Stack: React 19+ TypeScript, Vite, Tailwind CSS 4, shadcn/ui
- File upload: `react-dropzone` (hook-based, 7KB)
- State: plain `useState` + `useMemo` — no state management library needed
- API URL configurable via `VITE_API_URL` env var

## Setup Steps

### 1. Create Vite project
```bash
cd /home/vega/code-projects/relevancey
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. Install and configure Tailwind + shadcn/ui
```bash
npx shadcn@latest init
# Choose: New York style, Zinc color, CSS variables: yes

# Add needed components
npx shadcn@latest add slider button card badge progress accordion
```

### 3. Install react-dropzone
```bash
npm install react-dropzone
```

### 4. Configure environment
Create `frontend/.env`:
```
VITE_API_URL=http://localhost:8000
```

## Files to Implement

### 1. `frontend/src/types.ts` — Shared types
```typescript
export interface MatchedCard {
  note_id: number;
  text: string;
  extra: string;
  tags: string[];
  notetype: string;
  similarity: number;
  raw_fields: Record<string, string>;
}

export interface MatchResults {
  session_id: string;
  cards: MatchedCard[];
}

export interface UploadResponse {
  session_id: string;
  file_count: number;
  total_chunks: number;
  match_count: number;
  status: string;
}
```

### 2. `frontend/src/components/FileUpload.tsx` — Drag-and-drop upload
Key requirements:
- Use `useDropzone` hook from `react-dropzone`
- Accepted types: PDF, PPTX, DOCX, TXT, MD
- Max 50MB per file, max 5 files
- Show file list with status indicators (pending, uploading, done, error)
- Upload progress bar using `XMLHttpRequest` (fetch doesn't support upload progress)
- On success, call `onUploadComplete(sessionId)` callback
- Visually distinct drag-active state

The upload sends a `POST /api/upload` with `FormData` containing the files. The response includes `session_id` which is used for all subsequent API calls.

```tsx
const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};
```

UI layout:
```
┌─────────────────────────────────────────────┐
│                                             │
│   Drag & drop lecture files here,           │
│   or click to browse                        │
│                                             │
│   PDF, PPTX, DOCX, TXT, MD                │
│   (max 50MB, up to 5 files)               │
│                                             │
└─────────────────────────────────────────────┘

  lecture1.pdf           ████████████ 100%  ✓
  slides.pptx            ██████░░░░░░  52%

  [Upload & Find Relevant Cards]
```

### 3. `frontend/src/App.tsx` — Main app shell
Simple layout:
```tsx
export default function App() {
  const [results, setResults] = useState<MatchResults | null>(null);
  const [threshold, setThreshold] = useState(0.3);
  const [loading, setLoading] = useState(false);

  // Client-side filtering
  const filteredCards = useMemo(() => {
    if (!results) return [];
    return results.cards.filter(c => c.similarity >= threshold);
  }, [results, threshold]);

  const handleUploadComplete = async (sessionId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/match/${sessionId}`);
      const data = await res.json();
      setResults(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <header>
        <h1 className="text-2xl font-bold">Relevancey</h1>
        <p className="text-gray-500">Match your lecture materials to AnKing cards</p>
      </header>

      <FileUpload onUploadComplete={handleUploadComplete} apiUrl={API_URL} />

      {loading && <LoadingSpinner />}

      {results && (
        <>
          <RelevancySlider ... />
          <CardList ... />
          <SyncToAnki ... />
        </>
      )}
    </div>
  );
}
```

Note: `RelevancySlider`, `CardList`, and `SyncToAnki` components are implemented in prompts 10 and 11. For now, just render placeholder `<div>` elements so the app compiles.

## Verification
```bash
cd frontend
npm run dev
# Opens http://localhost:5173
```

- Page loads with header and file upload area
- Drag-and-drop zone highlights on drag-over
- Files can be selected via click or drop
- Invalid file types are rejected with error message
- Upload progress is shown
- After upload, `onUploadComplete` fires with session ID
