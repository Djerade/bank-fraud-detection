"use client";

import clsx from "clsx";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DashboardSnapshot } from "@/lib/types";
import { riskLevel, riskTone } from "@/lib/risk";
import { WorldMap } from "@/components/world-map";
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

type TimeRange = "today" | "week" | "year";
type ViewMode = "all" | "alerts";
type Theme = "light" | "dark";

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

function IconSun() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconMoon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" strokeLinecap="round" strokeLinejoin="round" />
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

function LoadingSkeleton({ error }: { error: string | null }) {
  return (
    <div className="td-skeleton-shell" aria-live="polite" aria-busy={!error}>
      {error ? (
        <div className="td-card td-loading err">Flux interrompu : {error}</div>
      ) : (
        <div className="td-card td-loading">Chargement du tableau de bord…</div>
      )}
      <div className="td-skeleton-row a">
        <div className="td-skeleton-block" />
        <div className="td-skeleton-block" />
        <div className="td-skeleton-block" />
      </div>
      <div className="td-skeleton-row b">
        <div className="td-skeleton-block" style={{ minHeight: 260 }} />
        <div className="td-skeleton-block" style={{ minHeight: 260 }} />
      </div>
      <div className="td-skeleton-block" style={{ height: 200 }} />
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [timeRange, setTimeRange] = useState<TimeRange>("week");
  const [viewMode, setViewMode] = useState<ViewMode>("all");
  const [theme, setTheme] = useState<Theme>("light");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notifOpen, setNotifOpen] = useState(false);
  const prevMetricsRef = useRef<DashboardSnapshot["metrics"] | null>(null);
  const [deltaTotal, setDeltaTotal] = useState<number | null>(null);
  const [deltaAlerts, setDeltaAlerts] = useState<number | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    setTheme(current === "dark" ? "dark" : "light");
  }, []);

  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus();
  }, [searchOpen]);

  useEffect(() => {
    if (!notifOpen) return;
    const onClick = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [notifOpen]);

  const toggleFullscreen = useCallback(async () => {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    } else {
      await document.exitFullscreen();
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem("td-theme", next);
      } catch {
        // stockage indisponible (navigation privée…) : le thème reste actif pour la session
      }
      return next;
    });
  }, []);

  const closeSearch = useCallback(() => {
    setSearchOpen(false);
    setSearchQuery("");
  }, []);

  const body = useMemo(() => {
    if (loading || !data) {
      return <LoadingSkeleton error={error} />;
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

    const baseTransactions =
      viewMode === "alerts"
        ? data.recentTransactions.filter((tx) => tx.fraud_predicted === 1)
        : data.recentTransactions;

    const query = searchQuery.trim().toLowerCase();
    const tableTransactions = query
      ? baseTransactions.filter(
          (tx) =>
            tx.transaction_id.toLowerCase().includes(query) ||
            tx.transaction_location.toLowerCase().includes(query)
        )
      : baseTransactions;

    const tickerItems = baseTransactions
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
            <button type="button" className={clsx(viewMode === "all" && "is-active")} onClick={() => setViewMode("all")}>
              Tableau de bord
            </button>
            <button
              type="button"
              className={clsx(viewMode === "alerts" && "is-active")}
              onClick={() => setViewMode("alerts")}
            >
              Alertes
            </button>
            <button type="button" disabled title="Bientôt disponible">
              Flux
            </button>
            <button type="button" disabled title="Bientôt disponible">
              Rapports
            </button>
          </nav>

          <div className="td-header-actions">
            <div className="td-header-pop-wrap">
              {searchOpen ? (
                <input
                  ref={searchInputRef}
                  type="text"
                  className="td-search-input"
                  placeholder="ID transaction ou ville…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") closeSearch();
                  }}
                  onBlur={() => {
                    if (!searchQuery) setSearchOpen(false);
                  }}
                  aria-label="Rechercher une transaction"
                />
              ) : (
                <button type="button" className="td-icon-btn" aria-label="Rechercher" onClick={() => setSearchOpen(true)}>
                  <IconSearch />
                </button>
              )}
            </div>

            <div className="td-header-pop-wrap" ref={notifRef}>
              <button
                type="button"
                className={clsx("td-icon-btn", notifOpen && "is-on")}
                aria-label="Notifications"
                aria-expanded={notifOpen}
                onClick={() => setNotifOpen((v) => !v)}
                style={{ position: "relative" }}
              >
                <IconBell />
                {data.metrics.criticalAlerts > 0 && <span className="td-badge-dot" aria-hidden />}
              </button>
              {notifOpen && (
                <div className="td-header-pop" role="menu">
                  <div className="td-header-pop-title">{nf(data.metrics.criticalAlerts)} alertes critiques</div>
                  {data.criticalTransactions.length === 0 ? (
                    <div className="td-header-pop-empty">Aucune alerte critique pour l&apos;instant.</div>
                  ) : (
                    data.criticalTransactions.slice(0, 5).map((tx) => (
                      <div key={tx.transaction_id} className="td-notif-row">
                        <div className="td-notif-row-top">
                          <span>{tx.transaction_id}</span>
                          <span style={{ color: riskTone("critical") }}>{tx.fraud_score.toFixed(3)}</span>
                        </div>
                        <div className="td-notif-row-sub">
                          {tx.transaction_location} · {tx.transaction_type}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <button
              type="button"
              className="td-icon-btn"
              aria-label={theme === "dark" ? "Activer le thème clair" : "Activer le thème sombre"}
              title={theme === "dark" ? "Thème clair" : "Thème sombre"}
              onClick={toggleTheme}
            >
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>

            <button type="button" className="td-icon-btn" aria-label="Réglages" disabled title="Bientôt disponible">
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
          <div className="td-ticker-tag">{viewMode === "alerts" ? "ALERTES SEULEMENT" : "TEMPS RÉEL"}</div>
          <div className="td-ticker-track">
            <div className="td-ticker-inner">
              {tickerItems || "Aucune transaction à afficher pour ce filtre."}
            </div>
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

            <div className="td-card" id="td-journal">
              <div className="td-card-head">
                <div>
                  <h3>Journal des transactions</h3>
                  <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                    {query || viewMode === "alerts"
                      ? `${nf(tableTransactions.length)} résultat(s) filtré(s)`
                      : "Dernières lignes scorées"}
                  </div>
                </div>
              </div>
              <div className="td-journal-list">
                {tableTransactions.length === 0 ? (
                  <div className="td-journal-empty">Aucune transaction ne correspond à ce filtre.</div>
                ) : (
                  tableTransactions.slice(0, 80).map((tx) => {
                    const level = riskLevel(tx.fraud_score);
                    return (
                      <div key={`${tx.transaction_id}-${tx.timestamp}`} className="td-journal-row">
                        <div className="td-journal-row-top">
                          <span>{tx.transaction_id}</span>
                          <span className="td-journal-badge" style={riskBadgeStyle(level)}>
                            {level.toUpperCase()}
                          </span>
                        </div>
                        <div className="td-journal-row-sub">
                          <span>
                            {new Date(tx.timestamp).toLocaleTimeString("fr-FR")} · {tx.transaction_type} ·{" "}
                            {tx.transaction_location}
                          </span>
                          <span style={{ fontVariantNumeric: "tabular-nums" }}>{tx.fraud_score.toFixed(3)}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
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
    toggleFullscreen,
    viewMode,
    theme,
    toggleTheme,
    searchOpen,
    searchQuery,
    closeSearch,
    notifOpen
  ]);

  return <main className="td-shell">{body}</main>;
}
