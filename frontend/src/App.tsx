import { useCallback, useMemo, useState, useEffect, useRef } from "react";
import { FileUpload } from "@/components/FileUpload";
import { RelevancySlider } from "@/components/RelevancySlider";
import { CardList } from "@/components/CardList";
import { CardDetailPanel } from "@/components/CardDetailPanel";
import { TagFilter } from "@/components/TagFilter";
import { KeywordFilter } from "@/components/KeywordFilter";
import { SyncToAnki } from "@/components/SyncToAnki";
import { RetroLoadingBar, PHASES } from "@/components/RetroLoadingBar";
import { SimilarityHistogram } from "@/components/SimilarityHistogram";
import { CoveragePieChart } from "@/components/CoveragePieChart";
import { ScrollToBottom } from "@/components/ScrollToBottom";
import type { MatchResults } from "@/types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8020";

export default function App() {
  const [results, setResults] = useState<MatchResults | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [threshold, setThreshold] = useState(0.3);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [processingPhase, setProcessingPhase] = useState(0);
  const phaseInterval = useRef<ReturnType<typeof setInterval>>(null);

  // Selection state — all selected by default
  const [deselectedIds, setDeselectedIds] = useState<Set<number>>(new Set());

  // Filter state
  const [stepFilter, setStepFilter] = useState<"step1" | "step2" | null>(null);
  const [tagFilters, setTagFilters] = useState<Set<string>>(new Set());
  const [keywordFilters, setKeywordFilters] = useState<Set<string>>(new Set());

  // Detail panel state
  const [pinnedCardId, setPinnedCardId] = useState<number | null>(null);
  const [hoveredCardId, setHoveredCardId] = useState<number | null>(null);

  // Reset filters when new results come in
  useEffect(() => {
    if (results) {
      setDeselectedIds(new Set());
      setStepFilter(null);
      setTagFilters(new Set());
      setKeywordFilters(new Set());
      setPinnedCardId(null);
      setHoveredCardId(null);
    }
  }, [results]);

  // Filter pipeline: threshold → step → tags → keywords
  const filteredCards = useMemo(() => {
    if (!results) return [];

    return results.cards.filter((c) => {
      // Threshold
      if (c.similarity < threshold) return false;

      // Step filter
      if (stepFilter === "step1" && !c.tags.some((t) => t.includes("AK_Step1"))) return false;
      if (stepFilter === "step2" && !c.tags.some((t) => t.includes("AK_Step2"))) return false;

      // Tag filters (OR — card must have at least one selected tag)
      if (tagFilters.size > 0) {
        const cardTopTags = c.tags.map((t) => {
          const parts = t.replace(/^#/, "").split("::");
          return parts.length > 1 && parts[0].startsWith("AK_") ? parts[1] : parts[0];
        });
        if (!cardTopTags.some((t) => tagFilters.has(t))) return false;
      }

      // Keyword filters (AND — card text must contain ALL selected keywords)
      if (keywordFilters.size > 0) {
        const textLower = `${c.text} ${c.extra}`.toLowerCase();
        for (const kw of keywordFilters) {
          if (!textLower.includes(kw.toLowerCase())) return false;
        }
      }

      return true;
    });
  }, [results, threshold, stepFilter, tagFilters, keywordFilters]);

  // Selected IDs = filtered cards minus deselected
  const selectedIds = useMemo(() => {
    const ids = new Set<number>();
    for (const c of filteredCards) {
      if (!deselectedIds.has(c.note_id)) {
        ids.add(c.note_id);
      }
    }
    return ids;
  }, [filteredCards, deselectedIds]);

  const toggleSelect = useCallback((noteId: number) => {
    setDeselectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(noteId)) {
        next.delete(noteId);
      } else {
        next.add(noteId);
      }
      return next;
    });
  }, []);

  const toggleKeyword = useCallback((kw: string) => {
    setKeywordFilters((prev) => {
      const next = new Set(prev);
      if (next.has(kw)) {
        next.delete(kw);
      } else {
        next.add(kw);
      }
      return next;
    });
  }, []);

  // Detail panel: show hovered or pinned card
  const detailCard = useMemo(() => {
    const id = pinnedCardId ?? hoveredCardId;
    if (!id || !results) return null;
    return results.cards.find((c) => c.note_id === id) ?? null;
  }, [pinnedCardId, hoveredCardId, results]);

  // Cycle through processing phases while loading
  useEffect(() => {
    if (loading) {
      setProcessingPhase(0);
      phaseInterval.current = setInterval(() => {
        setProcessingPhase((prev) => (prev + 1) % PHASES.length);
      }, 2500);
    } else {
      if (phaseInterval.current) clearInterval(phaseInterval.current);
    }
    return () => {
      if (phaseInterval.current) clearInterval(phaseInterval.current);
    };
  }, [loading]);

  const handleUploadComplete = (sessionId: string, uploadKeywords: string[]) => {
    setLoading(true);
    setLoadError(null);
    setKeywords(uploadKeywords);

    const POLL_INTERVAL = 3000;
    const MAX_ATTEMPTS = 80; // ~4 minutes
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        const res = await fetch(`${API_URL}/api/match/${sessionId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: MatchResults = await res.json();

        if (data.status === "processing") {
          if (attempts >= MAX_ATTEMPTS) {
            setLoadError("Processing timed out — please try again.");
            setLoading(false);
            return;
          }
          setTimeout(poll, POLL_INTERVAL);
        } else if (data.status === "error") {
          setLoadError("Processing failed on the server — please try again.");
          setLoading(false);
        } else {
          if (data.keywords.length > 0) setKeywords(data.keywords);
          setResults(data);
          setLoading(false);
        }
      } catch (e) {
        setLoadError(e instanceof Error ? e.message : "Failed to fetch results");
        setLoading(false);
      }
    };

    poll();
  };

  // Sync note IDs = selected cards that pass all filters
  const syncNoteIds = useMemo(
    () => filteredCards.filter((c) => selectedIds.has(c.note_id)).map((c) => c.note_id),
    [filteredCards, selectedIds],
  );

  return (
    <div className="min-h-screen bg-[#f1f1f1]">
      {/* Retro header */}
      <header className="bg-[#15314b] retro-scanlines">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <h1 className="font-mono text-3xl font-bold text-white retro-glow tracking-tight">
            RELEVANCEY
          </h1>
          <p className="font-mono text-sm text-[#83aace] mt-1 tracking-wide">
            Match your lecture materials to AnKing cards
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6 space-y-8">
        <FileUpload onUploadComplete={handleUploadComplete} apiUrl={API_URL} />

        {loading && <RetroLoadingBar label={PHASES[processingPhase]} />}

        {loadError && <p className="text-[#cb333b] text-sm">{loadError}</p>}

        {results && !loading && (
          <div className="space-y-6">
            <RelevancySlider
              value={threshold}
              onChange={setThreshold}
              totalCards={results.cards.length}
              filteredCards={filteredCards.length}
            />

            {/* Charts grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 bg-white rounded-lg border p-4">
                <h3 className="font-mono text-xs text-[#646469] mb-2 tracking-wider uppercase">
                  Similarity Distribution
                </h3>
                <SimilarityHistogram cards={results.cards} threshold={threshold} />
              </div>
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-mono text-xs text-[#646469] mb-2 tracking-wider uppercase">
                  Coverage
                </h3>
                <CoveragePieChart cards={results.cards} threshold={threshold} />
              </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg border p-4 space-y-4">
              <h3 className="font-mono text-xs text-[#646469] tracking-wider uppercase">
                Filters
              </h3>
              <TagFilter
                cards={filteredCards}
                stepFilter={stepFilter}
                onStepFilterChange={setStepFilter}
                tagFilters={tagFilters}
                onTagFiltersChange={setTagFilters}
              />
              <KeywordFilter
                keywords={keywords}
                activeKeywords={keywordFilters}
                onToggle={toggleKeyword}
                onClear={() => setKeywordFilters(new Set())}
              />
            </div>

            {/* Card count summary */}
            <div className="flex items-center justify-between text-sm">
              <span className="font-mono text-[#646469]">
                {filteredCards.length} cards shown · {syncNoteIds.length} selected for sync
              </span>
              {deselectedIds.size > 0 && (
                <button
                  className="text-xs text-[#3172ae] hover:underline"
                  onClick={() => setDeselectedIds(new Set())}
                >
                  Re-select all
                </button>
              )}
            </div>

            <CardList
              cards={filteredCards}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
              onHover={setHoveredCardId}
              onPin={(id) => setPinnedCardId(pinnedCardId === id ? null : id)}
              pinnedId={pinnedCardId}
            />

            <SyncToAnki
              noteIds={syncNoteIds}
              sessionId={results.session_id}
              threshold={threshold}
              apiUrl={API_URL}
            />
          </div>
        )}
      </main>

      {/* Detail side panel */}
      <CardDetailPanel
        card={detailCard}
        pinned={pinnedCardId !== null}
        selected={detailCard ? selectedIds.has(detailCard.note_id) : false}
        onClose={() => {
          setPinnedCardId(null);
          setHoveredCardId(null);
        }}
        onToggleSelect={toggleSelect}
      />

      <ScrollToBottom />
    </div>
  );
}
