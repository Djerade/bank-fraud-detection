"use client";

import { useEffect, useRef, useState } from "react";
import type { DashboardSnapshot } from "@/lib/types";

/** Polling partagé du snapshot dashboard (toutes les 2s) + delta entre les deux derniers relevés. */
export function useDashboardFeed() {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [deltaTotal, setDeltaTotal] = useState<number | null>(null);
  const [deltaAlerts, setDeltaAlerts] = useState<number | null>(null);
  const prevMetricsRef = useRef<DashboardSnapshot["metrics"] | null>(null);

  useEffect(() => {
    let alive = true;

    const load = async () => {
      try {
        const res = await fetch("/api/dashboard", { cache: "no-store" });
        if (!res.ok) {
          throw new Error(`API ${res.status}`);
        }
        const payload = (await res.json()) as DashboardSnapshot;
        if (!alive) return;

        const prev = prevMetricsRef.current;
        if (prev) {
          setDeltaTotal(payload.metrics.total - prev.total);
          setDeltaAlerts(payload.metrics.alerts - prev.alerts);
        } else {
          setDeltaTotal(null);
          setDeltaAlerts(null);
        }
        prevMetricsRef.current = payload.metrics;

        setData(payload);
        setError(null);
        setLoading(false);
      } catch (err) {
        if (alive) {
          setError(err instanceof Error ? err.message : "Erreur");
          setLoading(false);
        }
      }
    };

    load();
    const id = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const id = setInterval(() => setRefreshTick((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, []);

  return { data, loading, error, refreshTick, deltaTotal, deltaAlerts };
}
