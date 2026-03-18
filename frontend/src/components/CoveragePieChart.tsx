import { useMemo } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { TUFTS } from "@/lib/similarity-colors";
import type { MatchedCard } from "@/types";

interface Props {
  cards: MatchedCard[];
  threshold: number;
}

export function CoveragePieChart({ cards, threshold }: Props) {
  const { above, below, pct } = useMemo(() => {
    const aboveCount = cards.filter(c => c.similarity >= threshold).length;
    return {
      above: aboveCount,
      below: cards.length - aboveCount,
      pct: cards.length > 0 ? Math.round((aboveCount / cards.length) * 100) : 0,
    };
  }, [cards, threshold]);

  const data = [
    { name: "Above", value: above },
    { name: "Below", value: below },
  ];

  const colors = [TUFTS.primary, "#d1d5db"];

  return (
    <div className="flex flex-col items-center">
      <div className="w-full h-44 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="55%"
              outerRadius="80%"
              dataKey="value"
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={colors[i]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="font-mono text-3xl font-bold text-[#15314b]">{pct}%</span>
        </div>
      </div>
      <p className="text-xs text-[#646469] font-mono text-center mt-1">
        {above} / {cards.length} cards above {(threshold * 100).toFixed(0)}%
      </p>
    </div>
  );
}
