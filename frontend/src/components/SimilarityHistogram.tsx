import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { TUFTS } from "@/lib/similarity-colors";
import type { MatchedCard } from "@/types";

interface Props {
  cards: MatchedCard[];
  threshold: number;
}

const BIN_LABELS = [
  "0.0-0.1", "0.1-0.2", "0.2-0.3", "0.3-0.4", "0.4-0.5",
  "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0",
];

export function SimilarityHistogram({ cards, threshold }: Props) {
  const data = useMemo(() => {
    const bins = Array(10).fill(0) as number[];
    for (const card of cards) {
      const idx = Math.min(Math.floor(card.similarity * 10), 9);
      bins[idx]++;
    }
    return BIN_LABELS.map((label, i) => ({
      bin: label,
      count: bins[i],
      rangeStart: i / 10,
    }));
  }, [cards]);

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <XAxis
            dataKey="bin"
            tick={{ fontSize: 10, fontFamily: "Space Mono, monospace", fill: TUFTS.gray }}
            tickLine={false}
            axisLine={{ stroke: TUFTS.gray, strokeWidth: 0.5 }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 10, fontFamily: "Space Mono, monospace", fill: TUFTS.gray }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              fontFamily: "Space Mono, monospace",
              fontSize: 12,
              borderRadius: 4,
              border: `1px solid ${TUFTS.primary}`,
            }}
            formatter={(value: number | undefined) => [`${value ?? 0} cards`, "Count"]}
          />
          <ReferenceLine
            x={BIN_LABELS[Math.min(Math.floor(threshold * 10), 9)]}
            stroke={TUFTS.orange}
            strokeDasharray="4 3"
            strokeWidth={2}
            label={{
              value: `${(threshold * 100).toFixed(0)}%`,
              position: "top",
              fill: TUFTS.orange,
              fontSize: 11,
              fontFamily: "Space Mono, monospace",
            }}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.rangeStart >= threshold ? TUFTS.primary : TUFTS.primary}
                opacity={entry.rangeStart >= threshold ? 1 : 0.3}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
