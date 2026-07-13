"use client";

import { useMemo, useState } from "react";
import { riskBadgeStyle, riskLevel } from "@/lib/risk";
import { nf, pct } from "@/lib/format";
import { useDashboardFeed } from "@/lib/use-dashboard-feed";
import { WorldMap } from "@/components/world-map";
import {
  DashboardHeader,
  DashboardLoadingSkeleton,
  DashboardMetaBar,
  DashboardTicker
} from "@/components/dashboard-chrome";

export default function AlertsPage() {
  const { data, loading, error, refreshTick } = useDashboardFeed();
  const [searchQuery, setSearchQuery] = useState("");

  const body = useMemo(() => {
    if (loading || !data) {
      return <DashboardLoadingSkeleton error={error} />;
    }

    const alertTransactions = data.recentTransactions.filter((tx) => tx.fraud_predicted === 1);

    const query = searchQuery.trim().toLowerCase();
    const tableTransactions = query
      ? alertTransactions.filter(
          (tx) =>
            tx.transaction_id.toLowerCase().includes(query) || tx.transaction_location.toLowerCase().includes(query)
        )
      : alertTransactions;

    const tickerItems = alertTransactions
      .slice(0, 22)
      .map((tx) => {
        const level = riskLevel(tx.fraud_score);
        return `${tx.transaction_id} · ${tx.transaction_type} · ${tx.transaction_location} · ${tx.fraud_score.toFixed(3)} · ${level.toUpperCase()}`;
      })
      .join("   |   ");

    const maxLocAlerts = Math.max(1, ...data.byLocation.map((l) => l.alerts));
    const topLocations = data.byLocation.slice(0, 5);
    const nextRefreshIn = data.meta.refreshSeconds - (refreshTick % data.meta.refreshSeconds);

    return (
      <>
        <DashboardHeader data={data} searchQuery={searchQuery} onSearchQueryChange={setSearchQuery} />

        <DashboardTicker
          tag="ALERTES SEULEMENT"
          items={tickerItems || "Aucune alerte à afficher pour l'instant."}
        />

        <DashboardMetaBar
          source={data.meta.source}
          updatedAt={data.meta.updatedAt}
          nextRefreshIn={nextRefreshIn}
        />

        <section className="td-alerts-kpi-row">
          <div className="td-card">
            <div className="td-kpi-mini">
              <div className="td-kpi-icon orange">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 9v4M12 17h.01M10.3 3.3h3.4L21 17H3l6.7-13.7z" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <div className="td-kpi-num">{nf(data.metrics.alerts)}</div>
                <div className="td-kpi-label">Alertes ML</div>
              </div>
            </div>
          </div>

          <div className="td-card">
            <div className="td-kpi-mini">
              <div className="td-kpi-icon" style={riskBadgeStyle("critical")}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3z" />
                  <path d="M12 8v4M12 16h.01" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <div className="td-kpi-num">{nf(data.metrics.criticalAlerts)}</div>
                <div className="td-kpi-label">Alertes critiques (score ≥ 0,7)</div>
              </div>
            </div>
          </div>

          <div className="td-card">
            <div className="td-kpi-mini">
              <div className="td-kpi-icon blue">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 12h4l3 8 4-16 3 8h4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div>
                <div className="td-kpi-num">{pct(data.metrics.alertRatePct, 1)}</div>
                <div className="td-kpi-label">Taux d&apos;alerte global</div>
              </div>
            </div>
          </div>
        </section>

        <section className="td-card" style={{ marginTop: 18 }}>
          <div className="td-card-head">
            <div>
              <h3>Répartition géographique des alertes</h3>
              <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                Zones les plus sensibles
              </div>
            </div>
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
        </section>

        <section className="td-card" id="td-journal" style={{ marginTop: 18 }}>
          <div className="td-card-head">
            <div>
              <h3>Journal des alertes</h3>
              <div style={{ fontSize: 12, color: "var(--td-muted)", marginTop: 4 }}>
                {nf(tableTransactions.length)} alerte(s){query ? " (filtrées)" : ""}
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
                      Aucune alerte ne correspond à ce filtre.
                    </td>
                  </tr>
                ) : (
                  tableTransactions.slice(0, 150).map((tx) => {
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
  }, [data, loading, error, refreshTick, searchQuery]);

  return <main className="td-shell">{body}</main>;
}
