import { useMemo, useState } from "react";
import type { MatchedCard } from "@/types";
import { ChevronDown, ChevronUp, X } from "lucide-react";

interface Props {
  cards: MatchedCard[];
  stepFilter: "step1" | "step2" | null;
  onStepFilterChange: (step: "step1" | "step2" | null) => void;
  tagFilters: Set<string>;
  onTagFiltersChange: (tags: Set<string>) => void;
}

const MAX_VISIBLE_TAGS = 20;

function extractTopLevelTag(tag: string): string {
  // Get the first meaningful level: e.g. "#AK_Step1_v12::Cardiology" → "Cardiology"
  const parts = tag.replace(/^#/, "").split("::");
  // Skip the root prefix (AK_Step1_v12, AK_Step2_v12, AK_Other, etc.)
  if (parts.length > 1 && parts[0].startsWith("AK_")) {
    return parts[1];
  }
  return parts[0];
}

export function TagFilter({
  cards,
  stepFilter,
  onStepFilterChange,
  tagFilters,
  onTagFiltersChange,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  // Collect unique top-level tags with counts
  const tagCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const card of cards) {
      const seen = new Set<string>();
      for (const tag of card.tags) {
        const top = extractTopLevelTag(tag);
        if (!seen.has(top)) {
          seen.add(top);
          counts.set(top, (counts.get(top) ?? 0) + 1);
        }
      }
    }
    // Sort by count descending
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [cards]);

  const visibleTags = expanded ? tagCounts : tagCounts.slice(0, MAX_VISIBLE_TAGS);
  const hasMore = tagCounts.length > MAX_VISIBLE_TAGS;

  const toggleTag = (tag: string) => {
    const next = new Set(tagFilters);
    if (next.has(tag)) {
      next.delete(tag);
    } else {
      next.add(tag);
    }
    onTagFiltersChange(next);
  };

  const clearAll = () => {
    onStepFilterChange(null);
    onTagFiltersChange(new Set());
  };

  const hasActiveFilters = stepFilter !== null || tagFilters.size > 0;

  return (
    <div className="space-y-4">
      {/* Step filter big buttons */}
      <div className="flex items-center gap-3">
        <button
          className={`
            px-5 py-2.5 rounded-lg font-mono text-sm font-bold transition-all
            ${stepFilter === "step1"
              ? "bg-[#3172ae] text-white shadow-md"
              : "bg-[#eff5fb] text-[#3172ae] hover:bg-[#dce8f5]"
            }
          `}
          onClick={() => onStepFilterChange(stepFilter === "step1" ? null : "step1")}
        >
          Only Step 1
        </button>
        <button
          className={`
            px-5 py-2.5 rounded-lg font-mono text-sm font-bold transition-all
            ${stepFilter === "step2"
              ? "bg-[#3172ae] text-white shadow-md"
              : "bg-[#eff5fb] text-[#3172ae] hover:bg-[#dce8f5]"
            }
          `}
          onClick={() => onStepFilterChange(stepFilter === "step2" ? null : "step2")}
        >
          Only Step 2
        </button>

        {hasActiveFilters && (
          <button
            className="flex items-center gap-1 text-xs text-[#cb333b] hover:underline ml-auto"
            onClick={clearAll}
          >
            <X className="w-3 h-3" /> Clear filters
          </button>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-[#d1d5db]" />

      {/* Tag chips */}
      <div className="flex flex-wrap gap-1.5">
        {visibleTags.map(([tag, count]) => {
          const active = tagFilters.has(tag);
          return (
            <button
              key={tag}
              className={`
                px-2.5 py-1 rounded-full text-xs font-medium transition-all
                ${active
                  ? "bg-[#3172ae] text-white"
                  : "bg-[#eff5fb] text-[#15314b] hover:bg-[#dce8f5]"
                }
              `}
              onClick={() => toggleTag(tag)}
            >
              {tag}
              <span className={`ml-1 ${active ? "text-white/70" : "text-[#646469]"}`}>
                {count}
              </span>
            </button>
          );
        })}

        {hasMore && (
          <button
            className="px-2.5 py-1 rounded-full text-xs text-[#646469] hover:bg-[#eff5fb] transition-colors"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>Show less <ChevronUp className="w-3 h-3 inline" /></>
            ) : (
              <>{tagCounts.length - MAX_VISIBLE_TAGS} more <ChevronDown className="w-3 h-3 inline" /></>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
