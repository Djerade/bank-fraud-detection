import { NextResponse } from "next/server";

import type { DashboardSnapshot } from "@/lib/types";
import { resolveCityCoordinates } from "@/lib/geocode";

export const revalidate = 0;
export const dynamic = "force-dynamic";

const API_BASE = process.env.FRAUD_API_BASE?.trim() || "http://fraud-backend:8001";

/** Snapshot vide (backend indisponible) — évite de casser le rendu du dashboard. */
function emptySnapshot(): DashboardSnapshot {
  return {
    meta: { source: "kafka", updatedAt: new Date().toISOString(), refreshSeconds: 2 },
    metrics: {
      total: 0,
      alerts: 0,
      alertRatePct: 0,
      criticalAlerts: 0,
      avgAmountM: 0,
      uniqueClients: 0
    },
    series: [],
    byType: [],
    byMerchant: [],
    byLocation: [],
    scoreDistribution: [],
    criticalTransactions: [],
    recentTransactions: []
  };
}

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`backend HTTP ${res.status}`);
    }
    const data = (await res.json()) as DashboardSnapshot;
    data.byLocation = data.byLocation.map((loc) => ({
      ...loc,
      coords: resolveCityCoordinates(loc.name)
    }));
    return NextResponse.json(data);
  } catch (err) {
    console.error("[dashboard] backend injoignable:", err);
    return NextResponse.json(emptySnapshot());
  }
}
