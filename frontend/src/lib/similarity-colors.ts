/** Tufts palette colors mapped to similarity ranges */
export const TUFTS = {
  primary: "#3172ae",
  darkBlue: "#2a5c89",
  deepNavy: "#15314b",
  lightBlue: "#83aace",
  lightBlueBg: "#eff5fb",
  orange: "#d45d00",
  red: "#cb333b",
  green: "#62a60a",
  yellow: "#f1c400",
  teal: "#007f85",
  gray: "#646469",
  lightGrayBg: "#f1f1f1",
  nearBlack: "#161616",
} as const;

export function similarityColor(similarity: number): string {
  if (similarity >= 0.8) return TUFTS.green;
  if (similarity >= 0.6) return TUFTS.primary;
  if (similarity >= 0.4) return TUFTS.orange;
  return TUFTS.gray;
}

export function similarityClass(similarity: number): string {
  if (similarity >= 0.8) return "bg-[#62a60a]/15 text-[#62a60a] border-[#62a60a]/30";
  if (similarity >= 0.6) return "bg-[#3172ae]/15 text-[#3172ae] border-[#3172ae]/30";
  if (similarity >= 0.4) return "bg-[#d45d00]/15 text-[#d45d00] border-[#d45d00]/30";
  return "bg-[#646469]/15 text-[#646469] border-[#646469]/30";
}
