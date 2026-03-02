import { useMemo } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import type { MatchedCard } from "@/types";

const RESOURCE_FIELDS = [
  "Pathoma",
  "Boards and Beyond",
  "First Aid",
  "Sketchy",
  "OME",
  "Additional Resources",
];

const MAX_VISIBLE_TAGS = 6;

function formatTag(tag: string): string {
  return tag
    .replace(/^#/, "")
    .replace(/AK_Other::/g, "")
    .replace(/AK_Step1_v12::/g, "Step1 > ")
    .replace(/AK_Step2_v12::/g, "Step2 > ")
    .replaceAll("::", " > ");
}

function CardTags({ tags }: { tags: string[] }) {
  const formatted = useMemo(() => tags.map(formatTag), [tags]);
  const visible = formatted.slice(0, MAX_VISIBLE_TAGS);
  const extra = formatted.length - MAX_VISIBLE_TAGS;

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((tag, i) => (
        <Badge key={i} variant="secondary" className="text-xs font-normal">
          {tag}
        </Badge>
      ))}
      {extra > 0 && (
        <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
          +{extra} more
        </Badge>
      )}
    </div>
  );
}

function CardDetail({ card }: { card: MatchedCard }) {
  const resourceEntries = RESOURCE_FIELDS
    .map(field => ({ field, value: card.raw_fields[field] }))
    .filter(({ value }) => value && value.trim() && value.trim() !== "");

  return (
    <div className="space-y-3 pt-2">
      {card.extra && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Extra</p>
          <p className="text-sm">{card.extra}</p>
        </div>
      )}

      {resourceEntries.map(({ field, value }) => (
        <div key={field}>
          <p className="text-xs font-medium text-muted-foreground mb-1">{field}</p>
          <p className="text-sm">{value}</p>
        </div>
      ))}

      {card.tags.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Tags</p>
          <CardTags tags={card.tags} />
        </div>
      )}
    </div>
  );
}

interface Props {
  cards: MatchedCard[];
}

export function CardList({ cards }: Props) {
  if (cards.length === 0) {
    return (
      <p className="text-center text-muted-foreground py-8">
        No cards match at this threshold. Try lowering the slider.
      </p>
    );
  }

  return (
    <Accordion type="multiple" className="space-y-1">
      {cards.map(card => (
        <AccordionItem
          key={card.note_id}
          value={String(card.note_id)}
          className="border rounded-md px-3"
        >
          <AccordionTrigger className="hover:no-underline py-3">
            <div className="flex items-center gap-3 text-left w-full min-w-0">
              <Badge
                variant="outline"
                className="shrink-0 font-mono text-xs"
              >
                {(card.similarity * 100).toFixed(0)}%
              </Badge>
              <span className="truncate flex-1 text-sm">{card.text}</span>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <CardDetail card={card} />
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
