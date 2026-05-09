"use client";

import clsx from "clsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DashboardSnapshot } from "@/lib/types";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

function nf(value: number): string {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function pct(value: number, digits = 2): string {
  return `${value.toFixed(digits)} %`;
}

function minuteLabel(v: string): string {
  return new Date(v).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function riskLevel(score: number): "low" | "medium" | "high" | "critical" {
  if (score >= 0.85) return "critical";
  if (score >= 0.7) return "high";
  if (score >= 0.45) return "medium";
  return "low";
}

function riskTone(level: ReturnType<typeof riskLevel>): string {
  if (level === "critical") return "#dc2626";
  if (level === "high") return "#ea580c";
  if (level === "medium") return "#ca8a04";
  return "#16a34a";
}

type TimeRange = "today" | "week" | "year";

function filteredSeries(series: DashboardSnapshot["series"], range: TimeRange) {
  if (series.length === 0) return series;
  if (range === "today") return series.slice(-8);
  if (range === "week") return series.slice(-16);
  return series;
}

function sentimentFromThreat(threat01: number): { score: number; label: string; variant: "up" | "down" | "neutral" } {
  const score = Number(Math.max(1, Math.min(5, 5 - threat01 * 3.6)).toFixed(2));
  if (score >= 3.9) return { score, label: "Positif", variant: "up" };
  if (score >= 2.8) return { score, label: "Stable", variant: "neutral" };
  return { score, label: "À surveiller", variant: "down" };
}

function IconSearch() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-3-3" strokeLinecap="round" />
    </svg>
  );
}

function IconBell() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" strokeLinecap="round" />
      <path d="M13.73 21a2 2 0 01-3.46 0" strokeLinecap="round" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z" />
    </svg>
  );
}

function IconTrend({ up }: { up: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      {up ? (
        <path d="M6 15l6-6 6 6" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

function RiskGauge({ score, max = 5 }: { score: number; max?: number }) {
  const pctArc = Math.min(1, Math.max(0, score / max));
  const len = 219.9;
  const dash = pctArc * len;

  return (
    <svg className="td-gauge-svg" viewBox="0 0 200 108" aria-hidden>
      <defs>
        <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f87171" />
          <stop offset="50%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#4ade80" />
        </linearGradient>
      </defs>
      <path
        d="M 28 88 A 72 72 0 0 1 172 88"
        fill="none"
        stroke="#e2e8f0"
        strokeWidth="14"
        strokeLinecap="round"
      />
      <path
        d="M 28 88 A 72 72 0 0 1 172 88"
        fill="none"
        stroke="url(#gaugeGrad)"
        strokeWidth="14"
        strokeLinecap="round"
        strokeDasharray={`${dash} ${len}`}
        style={{ transition: "stroke-dasharray 0.6s ease" }}
      />
      <text x="46" y="102" fontSize="13" fill="#94a3b8">
        Risque
      </text>
      <text x="142" y="102" fontSize="13" fill="#94a3b8" textAnchor="end">
        Sain
      </text>
    </svg>
  );
}

const AVATAR_HUES = ["#2563eb", "#7c3aed", "#db2777", "#059669", "#d97706"];

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [timeRange, setTimeRange] = useState<TimeRange>("week");
  const prevMetricsRef = useRef<DashboardSnapshot["metrics"] | null>(null);
  const [deltaTotal, setDeltaTotal] = useState<number | null>(null);
  const [deltaAlerts, setDeltaAlerts] = useState<number | null>(null);

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

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    const kiosk = new URLSearchParams(window.location.search).get("kiosk") === "1";
    if (kiosk && !document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => undefined);
    }
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = useCallback(async () => {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  }, []);

  const body = useMemo(() => {
    if (loading || !data) {
      return (
        <div className={clsx("td-card td-loading", error && "err")}>
          {error ? `Flux interrompu : ${error}` : "Chargement du tableau de bord…"}
        </div>
      );
    }

    const threatIndex = Math.min(
      100,
      Math.round(data.metrics.alertRatePct * 1.15 + data.metrics.criticalAlerts * 0.08)
    );
    const threat01 = threatIndex / 100;
    const sentiment = sentimentFromThreat(threat01);
    const lastPoint = data.series[data.series.length - 1];
    const seriesSlice = filteredSeries(data.series, timeRange);
    const barData = seriesSlice.slice(-12).map((row) => ({
      name: minuteLabel(row.minute),
      vol: row.volume
    }));

    const tickerItems = data.recentTransactions
      .slice(0, 22)
      .map((tx) => {
        const level = riskLevel(tx.fraud_score);
        return `${tx.transaction_id} · ${tx.transaction_type} · ${tx.transaction_location} · ${tx.fraud_score.toFixed(3)} · ${level.toUpperCase()}`;
      })
      .join("   |   ");

    const maxLocAlerts = Math.max(1, ...data.byLocation.map((l) => l.alerts));
    const topLocations = data.byLocation.slice(0, 5);

    const nextRefreshIn = data.meta.refreshSeconds - (refreshTick % data.meta.refreshSeconds);

    const pillTotal =
      deltaTotal === null ? (
        <span className="td-pill neutral">—</span>
      ) : deltaTotal === 0 ? (
        <span className="td-pill neutral">Stable</span>
      ) : (
        <span className={clsx("td-pill", deltaTotal > 0 ? "up" : "down")}>
          <IconTrend up={deltaTotal > 0} />
          {deltaTotal > 0 ? "+" : ""}
          {nf(deltaTotal)}
        </span>
      );

    const pillAlerts =
      deltaAlerts === null ? (
        <span className="td-pill neutral">—</span>
      ) : deltaAlerts === 0 ? (
        <span className="td-pill neutral">Stable</span>
      ) : (
        <span className={clsx("td-pill", deltaAlerts < 0 ? "up" : "down")}>
          <IconTrend up={deltaAlerts < 0} />
          {deltaAlerts > 0 ? "+" : ""}
          {nf(deltaAlerts)}
        </span>
      );

    const avatarCount = Math.min(5, Math.max(3, Math.ceil(data.metrics.uniqueClients / 400)));

    return (
      <>
        <header className="td-header">
          <div className="td-brand">
            <span className="td-brand-mark">
              <IconShield />
            </span>
            FraudShield
          </div>

          <nav className="td-nav" aria-label="Navigation principale">
            <button type="button" className="is-active">
              Tableau de bord
            </button>
            <button type="button">Alertes</button>
            <button type="button">Flux</button>
            <button type="button">Rapports</button>
          </nav>

          <div className="td-header-actions">
            <button type="button" className="td-icon-btn" aria-label="Rechercher">
              <IconSearch />
            </button>
            <button type="button" className="td-icon-btn" aria-label="Notifications">
              <IconBell />
            </button>
            <button type="button" className="td-icon-btn" aria-label="Réglages">
              <IconSettings />
            </button>
            <button
              type="button"
              className="td-icon-btn"
              aria-label={isFullscreen ? "Quitter plein écran" : "Plein écran"}
              onClick={toggleFullscreen}
              title="Plein écran"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3H5a2 2 0 00-2 2v3M21 8V5a2 2 0 00-2-2h-3M3 16v3a2 2 0 002 2h3M16 21h3a2 2 0 002-2v-3" />
              </svg>
            </button>
            <span className="td-avatar" aria-hidden />
          </div>
        </header>

        <div className="td-ticker">
          <div className="td-ticker-tag">TEMPS RÉEL</div>
          <div className="td-ticker-track">
            <div className="td-ticker-inner">{tickerItems}</div>
          </div>
        </div>

        <div className="td-meta-bar">
          Source <strong>{data.meta.source}</strong> · MAJ {new Date(data.meta.updatedAt).toLocaleString("fr-FR")} ·
          Prochain rafraîchissement ~{nextRefreshIn}s
        </div>

        <section className="td-row-a">
          <div className="td-kpi-stack">
            <div className="td-card">
              <div className="td-kpi-mini">
                <div className="td-kpi-icon blue">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 19V5M8 19V9M12 19v-6M16 19v-3M20 19v-8" strokeLinecap="round" />
                  </svg>
                </div>
                <div style={{ flex: 1 }}>
                  <div className="td-card-head" style={{ marginBottom: 4 }}>
                    <div>
                      <div className="td-kpi-num">{nf(data.metrics.total)}</div>
                      <div className="td-kpi-label">Transactions analysées</div>
                    </div>
                    {pillTotal}
                  </div>
                </div>
              </div>
            </div>

            <div className="td-card">
              <div className="td-kpi-mini">
                <div className="td-kpi-icon orange">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 9v4M12 17h.01M10.3 3.3h3.4L21 17H3l6.7-13.7z" strokeLinecap="round" />
                  </svg>
                </div>
                <div style={{ flex: 1 }}>
                  <div className="td-card-head" style={{ marginBottom: 4 }}>
                    <div>
                      <div className="td-kpi-num">{nf(data.metrics.alerts)}</div>
                      <div className="td-kpi-label">Alertes ML</div>
                    </div>
                    {pillAlerts}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="td-card">
            <div className="td-card-head">
              <div>
                <h3>Volume par fenêtre</h3>
                <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                  Tx / minute (échantillon récent)
                </div>
              </div>
              <span className="td-pill up">
                <IconTrend up />
                {pct(data.metrics.alertRatePct)} alertes
              </span>
            </div>
            <div style={{ width: "100%", height: 240 }}>
              <ResponsiveContainer>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: "rgba(37, 99, 235, 0.06)" }}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--td-border)",
                      boxShadow: "var(--td-shadow)"
                    }}
                  />
                  <Bar dataKey="vol" fill="#fb923c" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="td-card">
            <div className="td-card-head">
              <div>
                <h3>Dynamique du flux</h3>
                <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                  Volume et alertes consolidés
                </div>
              </div>
              <div className="td-toggle-row">
                {(
                  [
                    ["today", "Aujourd'hui"],
                    ["week", "Semaine"],
                    ["year", "Année"]
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={clsx("td-chip", timeRange === key && "is-on")}
                    onClick={() => setTimeRange(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={seriesSlice}>
                  <defs>
                    <linearGradient id="tdVol" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="minute" tickFormatter={minuteLabel} tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                  <Tooltip
                    labelFormatter={(v) => new Date(String(v)).toLocaleString("fr-FR")}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--td-border)",
                      boxShadow: "var(--td-shadow)"
                    }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="#2563eb" strokeWidth={2} fill="url(#tdVol)" />
                  <Area type="monotone" dataKey="alerts" stroke="#fb923c" strokeWidth={2} fill="rgba(251, 146, 60, 0.08)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="td-row-b">
          <div className="td-card">
            <div className="td-card-head">
              <div>
                <h3>Répartition géographique</h3>
                <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                  Zones les plus sensibles (alertes)
                </div>
              </div>
              <button type="button" className="td-chip is-on" style={{ cursor: "pointer" }}>
                Exporter
              </button>
            </div>
            <div className="td-location-split">
              <div className="td-map-placeholder">
                <div className="td-map-dots">
                  {topLocations.slice(0, 4).map((_, i) => (
                    <span
                      key={i}
                      className="td-map-dot"
                      style={{
                        left: `${22 + i * 18}%`,
                        top: `${32 + (i % 3) * 14}%`
                      }}
                    />
                  ))}
                </div>
              </div>
              <div className="td-country-list">
                {topLocations.map((loc) => (
                  <div key={loc.name} className="td-country-row">
                    <div className="td-country-meta">
                      <span className="td-flag">📍</span>
                      {loc.name}
                    </div>
                    <div style={{ fontWeight: 700, color: "var(--td-blue)" }}>{pct(loc.ratePct, 1)}</div>
                    <div className="td-country-bar-wrap">
                      <div
                        className="td-country-bar"
                        style={{ width: `${Math.round((loc.alerts / maxLocAlerts) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="td-row-b-side">
            <div className="td-card">
              <div className="td-card-head">
                <div>
                  <h3>Indice de confiance</h3>
                  <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                    Synthèse risque / activité
                  </div>
                </div>
              </div>
              <div className="td-gauge-wrap">
                <RiskGauge score={sentiment.score} />
                <div className="td-gauge-center">
                  <div className="td-gauge-score">{sentiment.score}</div>
                  <span className={clsx("td-pill", sentiment.variant)}>{sentiment.label}</span>
                  <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 8 }}>
                    Menace globale {threatIndex}/100 · critiques {nf(data.metrics.criticalAlerts)}
                  </div>
                </div>
              </div>
            </div>

            <div className="td-card">
              <div className="td-card-head">
                <div>
                  <h3>Clients observés</h3>
                  <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                    Profils uniques dans la fenêtre
                  </div>
                </div>
              </div>
              <div className="td-kpi-num">{nf(data.metrics.uniqueClients)}</div>
              <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                Montant moyen {data.metrics.avgAmountM.toFixed(3)} M · Débit instantané{" "}
                {lastPoint ? `${nf(lastPoint.volume)} tx/min` : "—"}
              </div>
              <div className="td-avatar-row">
                <div className="td-avatar-stack" aria-hidden>
                  {Array.from({ length: avatarCount }).map((_, i) => (
                    <span
                      key={i}
                      className="td-stack-face"
                      style={{ background: AVATAR_HUES[i % AVATAR_HUES.length], zIndex: 5 - i }}
                    >
                      {String.fromCharCode(65 + i)}
                    </span>
                  ))}
                </div>
                <button type="button" className="td-show-all">
                  Voir tout →
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="td-card" style={{ marginTop: 18 }}>
          <div className="td-card-head">
            <div>
              <h3>Journal des transactions</h3>
              <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                Dernières lignes scorées
              </div>
            </div>
          </div>
          <div className="td-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Heure</th>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Montant</th>
                  <th>Score</th>
                  <th>Niveau</th>
                </tr>
              </thead>
              <tbody>
                {data.recentTransactions.slice(0, 80).map((tx) => {
                  const level = riskLevel(tx.fraud_score);
                  return (
                    <tr key={`${tx.transaction_id}-${tx.timestamp}`}>
                      <td>{new Date(tx.timestamp).toLocaleTimeString("fr-FR")}</td>
                      <td style={{ fontVariantNumeric: "tabular-nums" }}>{tx.transaction_id}</td>
                      <td>{tx.transaction_type}</td>
                      <td>{tx.transaction_amount_million.toFixed(2)}</td>
                      <td>{tx.fraud_score.toFixed(4)}</td>
                      <td style={{ color: riskTone(level), fontWeight: 700 }}>{level.toUpperCase()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </>
    );
  }, [
    data,
    loading,
    error,
    timeRange,
    refreshTick,
    deltaTotal,
    deltaAlerts,
    isFullscreen,
    toggleFullscreen
  ]);

  return <main className="td-shell">{body}</main>;
}
