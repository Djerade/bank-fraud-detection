"use client";

import clsx from "clsx";
import { useMemo, useState } from "react";
import type { DashboardSnapshot } from "@/lib/types";
import { riskBadgeStyle, riskLevel } from "@/lib/risk";
import { nf, pct, minuteLabel } from "@/lib/format";
import { IconTrend } from "@/lib/icons";
import { useDashboardFeed } from "@/lib/use-dashboard-feed";
import { WorldMap } from "@/components/world-map";
import {
  DashboardHeader,
  DashboardLoadingSkeleton,
  DashboardMetaBar,
  DashboardTicker
} from "@/components/dashboard-chrome";
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

function downloadLocationsCsv(rows: DashboardSnapshot["byLocation"]) {
  const header = "ville,alertes,taux_pct\n";
  const body = rows.map((r) => `${r.name},${r.alerts},${r.ratePct}`).join("\n");
  const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `fraudshield-zones-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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
        style={{ stroke: "var(--td-track)" }}
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
      <text x="46" y="102" fontSize="13" style={{ fill: "var(--td-muted)" }}>
        Risque
      </text>
      <text x="142" y="102" fontSize="13" style={{ fill: "var(--td-muted)" }} textAnchor="end">
        Sain
      </text>
    </svg>
  );
}

const AVATAR_HUES = ["#2563eb", "#7c3aed", "#db2777", "#059669", "#d97706"];

export default function DashboardPage() {
  const { data, loading, error, refreshTick, deltaTotal, deltaAlerts } = useDashboardFeed();
  const [timeRange, setTimeRange] = useState<TimeRange>("week");
  const [searchQuery, setSearchQuery] = useState("");

  const body = useMemo(() => {
    if (loading || !data) {
      return <DashboardLoadingSkeleton error={error} />;
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

    const query = searchQuery.trim().toLowerCase();
    const tableTransactions = query
      ? data.recentTransactions.filter(
          (tx) =>
            tx.transaction_id.toLowerCase().includes(query) || tx.transaction_location.toLowerCase().includes(query)
        )
      : data.recentTransactions;

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
        <DashboardHeader data={data} searchQuery={searchQuery} onSearchQueryChange={setSearchQuery} />

        <DashboardTicker tag="TEMPS RÉEL" items={tickerItems || "Aucune transaction à afficher."} />

        <DashboardMetaBar
          source={data.meta.source}
          updatedAt={data.meta.updatedAt}
          nextRefreshIn={nextRefreshIn}
        />

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
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--td-chart-grid)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: "var(--td-chart-tick)" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis tick={{ fontSize: 10, fill: "var(--td-chart-tick)" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: "rgba(37, 99, 235, 0.06)" }}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--td-border)",
                      boxShadow: "var(--td-shadow)",
                      background: "var(--td-chart-tooltip-bg)",
                      color: "var(--td-text)"
                    }}
                    labelStyle={{ color: "var(--td-text)" }}
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
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--td-chart-grid)" />
                  <XAxis
                    dataKey="minute"
                    tickFormatter={minuteLabel}
                    tick={{ fontSize: 10, fill: "var(--td-chart-tick)" }}
                  />
                  <YAxis tick={{ fontSize: 10, fill: "var(--td-chart-tick)" }} />
                  <Tooltip
                    labelFormatter={(v) => new Date(String(v)).toLocaleString("fr-FR")}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--td-border)",
                      boxShadow: "var(--td-shadow)",
                      background: "var(--td-chart-tooltip-bg)",
                      color: "var(--td-text)"
                    }}
                    labelStyle={{ color: "var(--td-text)" }}
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
              <button type="button" className="td-chip is-on" onClick={() => downloadLocationsCsv(data.byLocation)}>
                Exporter
              </button>
            </div>
            <div className="td-location-split">
              <WorldMap points={data.byLocation} maxAlerts={maxLocAlerts} />
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
                <button
                  type="button"
                  className="td-show-all"
                  onClick={() =>
                    document.getElementById("td-journal")?.scrollIntoView({ behavior: "smooth", block: "start" })
                  }
                >
                  Voir tout →
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="td-card" id="td-journal" style={{ marginTop: 18 }}>
          <div className="td-card-head">
            <div>
              <h3>Journal des transactions</h3>
              <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                {query ? `${nf(tableTransactions.length)} résultat(s) filtré(s)` : "Dernières lignes scorées"}
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
                  <th>Ville</th>
                  <th>Montant</th>
                  <th>Score</th>
                  <th>Niveau</th>
                </tr>
              </thead>
              <tbody>
                {tableTransactions.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="td-journal-empty">
                      Aucune transaction ne correspond à ce filtre.
                    </td>
                  </tr>
                ) : (
                  tableTransactions.slice(0, 80).map((tx) => {
                    const level = riskLevel(tx.fraud_score);
                    return (
                      <tr key={`${tx.transaction_id}-${tx.timestamp}`}>
                        <td>{new Date(tx.timestamp).toLocaleTimeString("fr-FR")}</td>
                        <td style={{ fontVariantNumeric: "tabular-nums" }}>{tx.transaction_id}</td>
                        <td>{tx.transaction_type}</td>
                        <td>{tx.transaction_location}</td>
                        <td>{tx.transaction_amount_million.toFixed(2)}</td>
                        <td style={{ fontVariantNumeric: "tabular-nums" }}>{tx.fraud_score.toFixed(4)}</td>
                        <td>
                          <span className="td-journal-badge" style={riskBadgeStyle(level)}>
                            {level.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </>
    );
  }, [data, loading, error, timeRange, refreshTick, deltaTotal, deltaAlerts, searchQuery]);

  return <main className="td-shell">{body}</main>;
}
