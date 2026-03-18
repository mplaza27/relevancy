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
      <div className="flex justify-between items-end">
        <div>
          <span className="text-sm font-medium">Relevancy Threshold</span>
        </div>
        <div className="text-right">
          <span className="font-mono text-4xl font-bold text-[#15314b] leading-none">
            {(value * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={0}
        max={1}
        step={0.01}
        className="w-full"
      />

      <div className="flex justify-between items-center">
        <span className="text-xs text-[#646469]">0% — More cards</span>
        <span className="text-sm font-mono font-medium text-[#3172ae] transition-all duration-200">
          {filteredCards} / {totalCards} cards
        </span>
        <span className="text-xs text-[#646469]">100% — Fewer cards</span>
      </div>
    </div>
  );
}
