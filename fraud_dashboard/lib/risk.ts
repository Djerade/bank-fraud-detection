export type RiskLevel = "low" | "medium" | "high" | "critical";

export function riskLevel(score: number): RiskLevel {
  if (score >= 0.85) return "critical";
  if (score >= 0.7) return "high";
  if (score >= 0.45) return "medium";
  return "low";
}

/** Teintes saturées, pensées pour un texte lisible sur fond clair (tableau, ticker). */
export function riskTone(level: RiskLevel): string {
  if (level === "critical") return "#dc2626";
  if (level === "high") return "#ea580c";
  if (level === "medium") return "#ca8a04";
  return "#16a34a";
}

/** Teintes lumineuses, pensées pour un marqueur/glow sur fond sombre (carte). */
export function riskToneGlow(level: RiskLevel): string {
  if (level === "critical") return "#f87171";
  if (level === "high") return "#fb923c";
  if (level === "medium") return "#fbbf24";
  return "#34d399";
}

export const RISK_LEGEND: Array<{ level: RiskLevel; label: string }> = [
  { level: "low", label: "Faible" },
  { level: "medium", label: "Moyen" },
  { level: "high", label: "Élevé" },
  { level: "critical", label: "Critique" }
];
