import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { similarityColor } from "@/lib/similarity-colors";
import type { MatchedCard } from "@/types";
import { X, Check, Square } from "lucide-react";

const RESOURCE_FIELDS = [
  "Pathoma",
  "Boards and Beyond",
  "First Aid",
  "Sketchy",
  "OME",
  "Additional Resources",
];

function formatTag(tag: string): string {
  return tag
    .replace(/^#/, "")
    .replace(/AK_Other::/g, "")
    .replace(/AK_Step1_v12::/g, "Step1 > ")
    .replace(/AK_Step2_v12::/g, "Step2 > ")
    .replaceAll("::", " > ");
}

interface Props {
  card: MatchedCard | null;
  pinned: boolean;
  selected: boolean;
  onClose: () => void;
  onToggleSelect: (noteId: number) => void;
}

export function CardDetailPanel({ card, pinned, selected, onClose, onToggleSelect }: Props) {
  if (!card) return null;

  const resourceEntries = RESOURCE_FIELDS
    .map((field) => ({ field, value: card.raw_fields[field] }))
    .filter(({ value }) => value && value.trim());

  const pct = (card.similarity * 100).toFixed(0);

  return (
    <div
      className={`
        fixed top-0 right-0 h-full w-[420px] max-w-[90vw]
        bg-white border-l border-[#d1d5db] shadow-xl
        overflow-y-auto z-50
        animate-slide-in
      `}
    >
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-[#d1d5db] px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className="font-mono text-2xl font-bold"
            style={{ color: similarityColor(card.similarity) }}
          >
            {pct}%
          </span>
          {pinned && (
            <span className="text-[10px] font-mono text-[#646469] bg-[#eff5fb] px-2 py-0.5 rounded">
              PINNED
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[#eff5fb] transition-colors"
        >
          <X className="w-5 h-5 text-[#646469]" />
        </button>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Select/deselect */}
        <Button
          variant={selected ? "outline" : "default"}
          size="sm"
          className="w-full"
          onClick={() => onToggleSelect(card.note_id)}
        >
          {selected ? (
            <>
              <Check className="w-4 h-4 mr-2" /> Selected
            </>
          ) : (
            <>
              <Square className="w-4 h-4 mr-2" /> Deselected — Click to re-select
            </>
          )}
        </Button>

        {/* Similarity bar */}
        <div>
          <p className="text-xs font-mono text-[#646469] mb-1">RELEVANCY</p>
          <div className="h-2 bg-[#eff5fb] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${pct}%`,
                backgroundColor: similarityColor(card.similarity),
              }}
            />
          </div>
        </div>

        {/* Full text */}
        <div>
          <p className="text-xs font-mono text-[#646469] mb-2">CARD TEXT</p>
          <p className="text-sm leading-relaxed">{card.text}</p>
        </div>

        {/* Extra */}
        {card.extra && (
          <div>
            <p className="text-xs font-mono text-[#646469] mb-2">EXTRA</p>
            <p className="text-sm leading-relaxed">{card.extra}</p>
          </div>
        )}

        {/* Resources */}
        {resourceEntries.length > 0 && (
          <div>
            <p className="text-xs font-mono text-[#646469] mb-2">RESOURCES</p>
            <div className="space-y-2">
              {resourceEntries.map(({ field, value }) => (
                <div key={field} className="bg-[#eff5fb] rounded-md px-3 py-2">
                  <p className="text-[10px] font-mono text-[#3172ae] font-medium mb-0.5">
                    {field}
                  </p>
                  <p className="text-sm">{value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tags */}
        {card.tags.length > 0 && (
          <div>
            <p className="text-xs font-mono text-[#646469] mb-2">TAGS</p>
            <div className="flex flex-wrap gap-1.5">
              {card.tags.map((tag, i) => (
                <Badge
                  key={i}
                  variant="secondary"
                  className="text-xs font-normal"
                >
                  {formatTag(tag)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Note type & ID */}
        <div className="pt-2 border-t border-[#d1d5db]">
          <p className="text-[10px] font-mono text-[#646469]">
            {card.notetype} · Note ID: {card.note_id}
          </p>
        </div>
      </div>
    </div>
  );
}
