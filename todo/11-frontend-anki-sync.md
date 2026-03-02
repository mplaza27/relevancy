[x]
# Prompt 11: Frontend Anki Sync UI

## Goal
Implement the "Sync to Anki" section of the frontend with all three methods: script download, search query copy, and note ID list download.

## Context
- Location: `frontend/src/components/SyncToAnki.tsx`
- Three methods are all MVP features, shown together in one section
- The script download hits the backend (bakes note IDs into the .py file)
- The search query and ID list can be generated client-side (no API call needed)
- The threshold from the slider determines which note IDs are included

## File to Implement

### `frontend/src/components/SyncToAnki.tsx`

Props:
- `noteIds: number[]` — filtered note IDs (from the currently visible cards after threshold)
- `sessionId: string` — for the script download API call
- `threshold: number` — current slider value (passed to script download endpoint)
- `apiUrl: string`

UI layout:
```
┌─────────────────────────────────────────────────────┐
│  Sync to Anki                                       │
│  142 cards selected at current threshold             │
│                                                      │
│  ── Recommended: AnkiConnect Script ──               │
│  Requires Anki + AnkiConnect add-on (code: 2055492159)│
│  Run with: python sync_relevancey.py                 │
│  [Download Sync Script (.py)]                        │
│                                                      │
│  ─────────────────────────────────────               │
│                                                      │
│  ── Manual Options ──                                │
│                                                      │
│  Paste into Anki Browse search bar:                  │
│  ┌────────────────────────────────────┐ [Copy]       │
│  │ deck:"AnKing Step Deck" nid:123... │              │
│  └────────────────────────────────────┘              │
│                                                      │
│  [Download Note ID List (.txt)]                      │
└─────────────────────────────────────────────────────┘
```

### Method A: Script Download
```tsx
const downloadScript = () => {
  const url = `${apiUrl}/api/sync/script?session_id=${sessionId}&threshold=${threshold}`;
  window.open(url, "_blank");
};
```

### Method B: Copy Search Query (Client-Side)
Build the Anki search query directly in the browser:
```typescript
const searchQuery = noteIds.length > 0
  ? `deck:"AnKing Step Deck" nid:${noteIds.join(",")}`
  : "";
```

Copy to clipboard:
```typescript
const copySearchQuery = async () => {
  await navigator.clipboard.writeText(searchQuery);
  setCopied(true);
  setTimeout(() => setCopied(false), 2000);
};
```

Show a truncated preview in a code block (first 200 chars + "..."). Show the full query only on hover/expand if it's long.

### Method C: Download Note ID List (Client-Side)
Generate a `.txt` file in the browser:
```typescript
const downloadIdList = () => {
  const content = noteIds.join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "relevancey_note_ids.txt";
  a.click();
  URL.revokeObjectURL(url);
};
```

### State
- `copied: boolean` — show "Copied!" feedback for 2 seconds

### Edge cases
- If `noteIds` is empty, disable all buttons and show: "No cards selected. Adjust the relevancy slider."
- Search query for thousands of IDs can be very long — the copy button still works, but truncate the preview display

## Integration with App.tsx
```tsx
<SyncToAnki
  noteIds={filteredCards.map(c => c.note_id)}
  sessionId={results.session_id}
  threshold={threshold}
  apiUrl={API_URL}
/>
```

## Verification
- "Download Sync Script" triggers a file download of `sync_relevancey.py`
- Opening the downloaded script shows correct note IDs
- "Copy" button copies the full search query to clipboard
- "Copied!" feedback appears and disappears after 2 seconds
- "Download Note ID List" creates a `.txt` with one ID per line
- All buttons are disabled when no cards are selected
- Changing the slider threshold updates the card count in the sync section
