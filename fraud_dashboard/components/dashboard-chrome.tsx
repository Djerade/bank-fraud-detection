"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DashboardSnapshot } from "@/lib/types";
import { nf } from "@/lib/format";
import { riskTone } from "@/lib/risk";
import { IconBell, IconMoon, IconSearch, IconSettings, IconShield, IconSun } from "@/lib/icons";

type Theme = "light" | "dark";

export function DashboardHeader({
  data,
  searchQuery,
  onSearchQueryChange
}: {
  data: DashboardSnapshot | null;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
}) {
  const pathname = usePathname();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [theme, setTheme] = useState<Theme>("light");
  const [searchOpen, setSearchOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
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
    onSearchQueryChange("");
  }, [onSearchQueryChange]);

  const criticalAlerts = data?.metrics.criticalAlerts ?? 0;
  const criticalTransactions = data?.criticalTransactions ?? [];

  return (
    <header className="td-header">
      <div className="td-brand">
        <span className="td-brand-mark">
          <IconShield />
        </span>
        FraudShield
      </div>

      <nav className="td-nav" aria-label="Navigation principale">
        <Link href="/" className={clsx(pathname === "/" && "is-active")}>
          Tableau de bord
        </Link>
        <Link href="/alertes" className={clsx(pathname === "/alertes" && "is-active")}>
          Alertes
        </Link>
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
              onChange={(e) => onSearchQueryChange(e.target.value)}
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
            {criticalAlerts > 0 && <span className="td-badge-dot" aria-hidden />}
          </button>
          {notifOpen && (
            <div className="td-header-pop" role="menu">
              <div className="td-header-pop-title">{nf(criticalAlerts)} alertes critiques</div>
              {criticalTransactions.length === 0 ? (
                <div className="td-header-pop-empty">Aucune alerte critique pour l&apos;instant.</div>
              ) : (
                criticalTransactions.slice(0, 5).map((tx) => (
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
  );
}

export function DashboardTicker({ tag, items }: { tag: string; items: string }) {
  return (
    <div className="td-ticker">
      <div className="td-ticker-tag">{tag}</div>
      <div className="td-ticker-track">
        <div className="td-ticker-inner">{items}</div>
      </div>
    </div>
  );
}

export function DashboardMetaBar({
  source,
  updatedAt,
  nextRefreshIn
}: {
  source: string;
  updatedAt: string;
  nextRefreshIn: number;
}) {
  return (
    <div className="td-meta-bar">
      Source <strong>{source}</strong> · MAJ {new Date(updatedAt).toLocaleString("fr-FR")} · Prochain
      rafraîchissement ~{nextRefreshIn}s
    </div>
  );
}

export function DashboardLoadingSkeleton({ error }: { error: string | null }) {
  return (
    <div className="td-skeleton-shell" aria-live="polite" aria-busy={!error}>
      {error ? (
        <div className="td-card td-loading err">Flux interrompu : {error}</div>
      ) : (
        <div className="td-card td-loading">Chargement…</div>
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
