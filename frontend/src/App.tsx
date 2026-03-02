import { useMemo, useState } from "react";
import { FileUpload } from "@/components/FileUpload";
import { RelevancySlider } from "@/components/RelevancySlider";
import { CardList } from "@/components/CardList";
import { SyncToAnki } from "@/components/SyncToAnki";
import type { MatchResults } from "@/types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [results, setResults] = useState<MatchResults | null>(null);
  const [threshold, setThreshold] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const filteredCards = useMemo(() => {
    if (!results) return [];
    return results.cards.filter(c => c.similarity >= threshold);
  }, [results, threshold]);

  const handleUploadComplete = async (sessionId: string) => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`${API_URL}/api/match/${sessionId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: MatchResults = await res.json();
      setResults(data);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to fetch results");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      <header>
        <h1 className="text-2xl font-bold">Relevancey</h1>
        <p className="text-muted-foreground">Match your lecture materials to AnKing cards</p>
      </header>

      <FileUpload onUploadComplete={handleUploadComplete} apiUrl={API_URL} />

      {loading && (
        <div className="text-center text-muted-foreground animate-pulse py-8">
          Finding relevant cards…
        </div>
      )}

      {loadError && (
        <p className="text-destructive text-sm">{loadError}</p>
      )}

      {results && !loading && (
        <div className="space-y-6">
          <RelevancySlider
            value={threshold}
            onChange={setThreshold}
            totalCards={results.cards.length}
            filteredCards={filteredCards.length}
          />

          <CardList cards={filteredCards} />

          <SyncToAnki
            noteIds={filteredCards.map(c => c.note_id)}
            sessionId={results.session_id}
            threshold={threshold}
            apiUrl={API_URL}
          />
        </div>
      )}
    </div>
  );
}
