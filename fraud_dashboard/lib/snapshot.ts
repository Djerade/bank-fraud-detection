import type { DashboardSnapshot, Transaction } from "@/lib/types";

export const REFRESH_SECONDS = 2;
export const ALERT_THRESHOLD = 0.7;

function minuteIso(timestamp: string): string {
  const date = new Date(timestamp);
  date.setSeconds(0, 0);
  return date.toISOString();
}

function asPercent(numerator: number, denominator: number): number {
  if (denominator <= 0) {
    return 0;
  }
  return Number(((numerator / denominator) * 100).toFixed(2));
}

function scoreHistogram(rows: Transaction[]): DashboardSnapshot["scoreDistribution"] {
  const bins = Array.from({ length: 10 }, (_, i) => ({
    bucket: `${(i / 10).toFixed(1)}-${((i + 1) / 10).toFixed(1)}`,
    count: 0
  }));
  rows.forEach((tx) => {
    const s = Number.isFinite(tx.fraud_score) ? Math.min(0.9999, Math.max(0, tx.fraud_score)) : 0;
    const idx = Math.min(9, Math.floor(s * 10));
    bins[idx].count += 1;
  });
  return bins;
}

export function buildDashboardSnapshot(
  rows: Transaction[],
  meta: { source: DashboardSnapshot["meta"]["source"]; refreshSeconds?: number }
): DashboardSnapshot {
  const refreshSeconds = meta.refreshSeconds ?? REFRESH_SECONDS;
  const total = rows.length;
  const alerts = rows.reduce((acc, tx) => acc + tx.fraud_predicted, 0);
  const critical = rows.filter((tx) => tx.fraud_score >= ALERT_THRESHOLD);
  const uniqueClients = new Set(rows.map((tx) => tx.customer_id)).size;
  const avgAmount =
    rows.reduce((acc, tx) => acc + tx.transaction_amount_million, 0) / Math.max(1, total);

  const byMinuteMap = new Map<string, { volume: number; alerts: number }>();
  rows.forEach((tx) => {
    const key = minuteIso(tx.timestamp);
    const current = byMinuteMap.get(key) ?? { volume: 0, alerts: 0 };
    current.volume += 1;
    current.alerts += tx.fraud_predicted;
    byMinuteMap.set(key, current);
  });
  const series = Array.from(byMinuteMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-20)
    .map(([minute, item]) => ({
      minute,
      volume: item.volume,
      alerts: item.alerts,
      alertRatePct: asPercent(item.alerts, item.volume)
    }));

  const groupBy = <T extends string>(selector: (tx: Transaction) => T) => {
    const map = new Map<T, { volume: number; alerts: number }>();
    rows.forEach((tx) => {
      const key = selector(tx);
      const current = map.get(key) ?? { volume: 0, alerts: 0 };
      current.volume += 1;
      current.alerts += tx.fraud_predicted;
      map.set(key, current);
    });
    return map;
  };

  const byType = Array.from(groupBy((tx) => tx.transaction_type).entries())
    .map(([name, v]) => ({ name, volume: v.volume, alerts: v.alerts }))
    .sort((a, b) => b.volume - a.volume);

  const byMerchant = Array.from(groupBy((tx) => tx.merchant_category).entries())
    .map(([name, v]) => ({
      name,
      volume: v.volume,
      alerts: v.alerts,
      ratePct: asPercent(v.alerts, v.volume)
    }))
    .sort((a, b) => b.alerts - a.alerts);

  const byLocation = Array.from(groupBy((tx) => tx.transaction_location).entries())
    .map(([name, v]) => ({
      name,
      alerts: v.alerts,
      ratePct: asPercent(v.alerts, v.volume)
    }))
    .sort((a, b) => b.alerts - a.alerts)
    .slice(0, 8);

  return {
    meta: {
      source: meta.source,
      updatedAt: new Date().toISOString(),
      refreshSeconds
    },
    metrics: {
      total,
      alerts,
      alertRatePct: asPercent(alerts, total),
      criticalAlerts: critical.length,
      avgAmountM: Number(avgAmount.toFixed(3)),
      uniqueClients
    },
    series,
    byType,
    byMerchant,
    byLocation,
    scoreDistribution: scoreHistogram(rows),
    criticalTransactions: critical
      .sort((a, b) => b.fraud_score - a.fraud_score)
      .slice(0, 100),
    recentTransactions: [...rows]
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 250)
  };
}
