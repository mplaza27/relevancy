import { useState } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  noteIds: number[];
  sessionId: string;
  threshold: number;
  apiUrl: string;
}

export function SyncToAnki({ noteIds, sessionId, threshold, apiUrl }: Props) {
  const [copied, setCopied] = useState(false);

  const disabled = noteIds.length === 0;

  const searchQuery = noteIds.length > 0
    ? `deck:"AnKing Step Deck" nid:${noteIds.join(",")}`
    : "";

  const queryPreview = searchQuery.length > 200
    ? `${searchQuery.slice(0, 200)}…`
    : searchQuery;

  const downloadScript = () => {
    const url = `${apiUrl}/api/sync/script?session_id=${encodeURIComponent(sessionId)}&threshold=${threshold}`;
    window.open(url, "_blank");
  };

  const copySearchQuery = async () => {
    await navigator.clipboard.writeText(searchQuery);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadIdList = () => {
    const content = noteIds.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "relevancy_note_ids.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="border rounded-lg p-5 space-y-5">
      <div>
        <h2 className="font-semibold text-lg">Sync to Anki</h2>
        {disabled ? (
          <p className="text-sm text-muted-foreground mt-1">
            No cards selected. Adjust the relevancy slider.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground mt-1">
            {noteIds.length} card{noteIds.length !== 1 ? "s" : ""} selected at current threshold
          </p>
        )}
      </div>

      {/* Method A: AnkiConnect Script */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted-foreground font-medium">Recommended: AnkiConnect Script</span>
          <div className="h-px flex-1 bg-border" />
        </div>
        <p className="text-xs text-muted-foreground">
          Requires Anki running + AnkiConnect add-on (code: 2055492159). Run with:{" "}
          <code className="font-mono">python sync_relevancy.py</code>
        </p>
        <Button onClick={downloadScript} disabled={disabled}>
          Download Sync Script (.py)
        </Button>
      </div>

      {/* Method B: Search Query */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs text-muted-foreground font-medium">Manual Options</span>
          <div className="h-px flex-1 bg-border" />
        </div>
        <p className="text-xs text-muted-foreground">Paste into Anki Browse search bar:</p>
        <div className="flex gap-2">
          <code className="flex-1 text-xs font-mono bg-muted rounded px-2 py-1 overflow-hidden truncate">
            {queryPreview || "—"}
          </code>
          <Button
            variant="outline"
            size="sm"
            onClick={copySearchQuery}
            disabled={disabled}
          >
            {copied ? "Copied!" : "Copy"}
          </Button>
        </div>
      </div>

      {/* Method C: Note ID List */}
      <div>
        <Button variant="outline" onClick={downloadIdList} disabled={disabled}>
          Download Note ID List (.txt)
        </Button>
      </div>
    </div>
  );
}
