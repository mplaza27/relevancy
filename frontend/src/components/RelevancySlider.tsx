import { Slider } from "@/components/ui/slider";

interface Props {
  value: number;
  onChange: (value: number) => void;
  totalCards: number;
  filteredCards: number;
}

export function RelevancySlider({ value, onChange, totalCards, filteredCards }: Props) {
  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium">Relevancy Threshold</span>
        <span className="text-sm text-muted-foreground font-mono">
          {filteredCards} / {totalCards} cards
        </span>
      </div>

      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={0}
        max={1}
        step={0.01}
        className="w-full"
      />

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>0.0 — More cards</span>
        <span className="font-mono font-medium text-foreground">{value.toFixed(2)}</span>
        <span>1.0 — Fewer cards</span>
      </div>
    </div>
  );
}
