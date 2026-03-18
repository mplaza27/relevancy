import { Badge } from "@/components/ui/badge";
import { similarityClass } from "@/lib/similarity-colors";
import type { MatchedCard } from "@/types";
import { Check, X } from "lucide-react";

interface Props {
  cards: MatchedCard[];
  selectedIds: Set<number>;
  onToggleSelect: (noteId: number) => void;
  onHover: (noteId: number | null) => void;
  onPin: (noteId: number) => void;
  pinnedId: number | null;
}

export function CardList({ cards, selectedIds, onToggleSelect, onHover, onPin, pinnedId }: Props) {
  if (cards.length === 0) {
    return (
      <p className="text-center text-[#646469] py-8">
        No cards match at this threshold. Try lowering the slider.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {cards.map((card) => {
        const selected = selectedIds.has(card.note_id);
        const isPinned = pinnedId === card.note_id;

        return (
          <div
            key={card.note_id}
            className={`
              relative group rounded-lg border p-3 cursor-pointer
              transition-all duration-150 select-none
              ${isPinned ? "ring-2 ring-[#3172ae] border-[#3172ae]" : "border-[#d1d5db]"}
              ${selected
                ? "bg-white hover:shadow-md"
                : "bg-[#f1f1f1] opacity-40"
              }
            `}
            onMouseEnter={() => onHover(card.note_id)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onPin(card.note_id)}
          >
            {/* Select/deselect checkbox */}
            <button
              className={`
                absolute top-2 right-2 w-5 h-5 rounded border flex items-center justify-center
                transition-colors z-10
                ${selected
                  ? "bg-[#3172ae] border-[#3172ae] text-white"
                  : "bg-white border-[#d1d5db] text-[#d1d5db] hover:border-[#3172ae]"
                }
              `}
              onClick={(e) => {
                e.stopPropagation();
                onToggleSelect(card.note_id);
              }}
              title={selected ? "Deselect card" : "Re-select card"}
            >
              {selected ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            </button>

            {/* Similarity badge */}
            <Badge
              variant="outline"
              className={`font-mono text-xs border mb-2 ${similarityClass(card.similarity)}`}
            >
              {(card.similarity * 100).toFixed(0)}%
            </Badge>

            {/* Card text preview */}
            <p className="text-sm leading-snug line-clamp-3 pr-5">
              {card.text}
            </p>

            {/* Notetype label */}
            <p className="text-[10px] text-[#646469] mt-2 font-mono truncate">
              {card.notetype}
            </p>
          </div>
        );
      })}
    </div>
  );
}
