interface Props {
  label?: string;
}

const PHASES = [
  "PARSING DOCUMENTS",
  "GENERATING EMBEDDINGS",
  "SEARCHING ANKING DATABASE",
  "RANKING MATCHES",
];

export function RetroLoadingBar({ label }: Props) {
  const displayLabel = label ?? PHASES[0];

  return (
    <div className="space-y-3 py-8">
      {/* Segmented bar */}
      <div className="h-3 w-full rounded-sm overflow-hidden bg-[#eff5fb] border border-[#d1d5db]">
        <div className="h-full retro-loading-bar" />
      </div>

      {/* Status text with blinking cursor */}
      <p className="text-center font-mono text-sm tracking-widest text-[#3172ae] retro-cursor">
        {displayLabel}
      </p>
    </div>
  );
}

export { PHASES };
