import { X } from "lucide-react";

interface Props {
  keywords: string[];
  activeKeywords: Set<string>;
  onToggle: (keyword: string) => void;
  onClear: () => void;
}

export function KeywordFilter({ keywords, activeKeywords, onToggle, onClear }: Props) {
  if (keywords.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-[#646469] tracking-wider uppercase">
          Document Keywords
        </p>
        {activeKeywords.size > 0 && (
          <button
            className="flex items-center gap-1 text-xs text-[#cb333b] hover:underline"
            onClick={onClear}
          >
            <X className="w-3 h-3" /> Clear
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {keywords.map((kw) => {
          const active = activeKeywords.has(kw);
          return (
            <button
              key={kw}
              className={`
                px-2.5 py-1 rounded-full text-xs font-mono transition-all border
                ${active
                  ? "bg-[#d45d00] text-white border-[#d45d00]"
                  : "bg-white text-[#15314b] border-[#d1d5db] hover:border-[#d45d00] hover:text-[#d45d00]"
                }
              `}
              onClick={() => onToggle(kw)}
            >
              {kw}
            </button>
          );
        })}
      </div>
    </div>
  );
}
